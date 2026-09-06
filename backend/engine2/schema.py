"""engine2 数据契约：会话状态 v2、分析输出、patch 合并。

- 会话状态为版本化 JSON（Conversation.state），v=2。
- 状态迁移策略（R-B4）：DB 行保留原状态，读取时经 normalize_state 做
  **只读迁移**（不主动写回），由下一次回合持久化；升级只允许“增字段+默认值”，
  禁止删除/改语义已有字段；未来 v2→v3 走同一登记 + 演练流程（见 docs/03 §4.1）。
- 节点产出 StatePatch（dict），由 pipeline 按 reducer 语义合并。
- 节点只读写 context.scratch（回合内临时数据），持久状态只经 patch 变更。
"""
import copy
from dataclasses import dataclass, field
from typing import Any

from engine2.errors import Engine2SchemaError
from models.database import Persona, Scenario
from pydantic import BaseModel, Field, ValidationError

STATE_VERSION = 2
FACT_LIMIT = 20

# 意图/事件优先级（从高到低），用于 primary 判定与战术路由
INTENT_ORDER = [
    "doubt_ai",
    "probe",
    "request_photo",
    "red_packet",
    "buy_intent",
    "objection",
    "meeting",
    "end_chat",
]
INTENTS = set(INTENT_ORDER) | {"casual"}

_TOP_KEYS = {"v", "stage", "meters", "facts", "photos", "economy", "negotiation", "flags"}
_MERGE_KEYS = {"meters"}  # facts 由 memory 节点整表重算后整体替换


def default_state_v2(scenario_slug: str | None = None) -> dict:
    return {
        "v": STATE_VERSION,
        "stage": {"scenario_slug": scenario_slug, "idx": 0, "turns": 0},
        "meters": {"trust": 10, "interest": 20, "suspicion": 0},
        "facts": {},
        "photos": {"sent": 0, "asked": 0, "refused": 0},
        "economy": {"red_packets": 0, "gifts": 0},
        "negotiation": {"last_pitch_round": None, "photo_warmth": 0},
        "flags": {},
    }


def _is_legacy_v1(raw: dict) -> bool:
    """旧引擎（frozen engine/）写入的扁平 state：无 v 字段 + 旧字段标记。"""
    if raw.get("v") is not None:
        return False
    return bool(set(raw) & {"stage_idx", "stage_turns", "photos_sent", "red_packets", "facts"})


def _apply_legacy_v1(out: dict, raw: dict) -> None:
    """v1 扁平 state → v2 映射（R-B4，保留旧会话进度，其余字段回退默认）。"""
    out["stage"]["idx"] = max(0, _as_int(raw.get("stage_idx"), 0))
    out["stage"]["turns"] = max(0, _as_int(raw.get("stage_turns"), 0))
    facts = raw.get("facts")
    if isinstance(facts, dict):
        out["facts"] = {str(k): str(v) for k, v in list(facts.items())[:FACT_LIMIT]}
    out["photos"]["sent"] = max(0, _as_int(raw.get("photos_sent"), 0))
    out["economy"]["red_packets"] = max(0, _as_int(raw.get("red_packets"), 0))


def _as_int(value: Any, default: int = 0, lo: int | None = 0) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        num = default
    if lo is not None and num < lo:
        num = lo
    return num


def _clamp100(value: Any) -> int:
    num = _as_int(value, 0, 0)
    return min(num, 100)


def normalize_state(raw: Any, scenario_slug: str | None = None) -> dict:
    """把 DB 读出的 state 归一化为合法的 v2 状态。

    读时迁移：v1 扁平旧数据按字段映射保留进度；无法识别的数据回退为新会话。
    """
    out = default_state_v2(scenario_slug)
    if not isinstance(raw, dict):
        return out
    if raw.get("v") == STATE_VERSION:
        for key, value in raw.items():
            if key not in _TOP_KEYS:
                continue
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                out[key].update(value)
            elif key != "v":
                out[key] = copy.deepcopy(value)
    elif _is_legacy_v1(raw):
        _apply_legacy_v1(out, raw)
    else:
        return out
    stage = out["stage"]
    stage["idx"] = max(0, _as_int(stage.get("idx"), 0))
    stage["turns"] = max(0, _as_int(stage.get("turns"), 0))
    out["meters"] = {
        "trust": _clamp100(out["meters"].get("trust", 10)),
        "interest": _clamp100(out["meters"].get("interest", 20)),
        "suspicion": _clamp100(out["meters"].get("suspicion", 0)),
    }
    for group in ("photos", "economy"):
        for key, default in (("sent", 0), ("asked", 0), ("refused", 0),
                             ("red_packets", 0), ("gifts", 0)):
            if key in out[group]:
                out[group][key] = max(0, _as_int(out[group].get(key), default))
    out["facts"] = {str(k): str(v) for k, v in list(out["facts"].items())[:FACT_LIMIT]}
    if not isinstance(out["negotiation"], dict):
        out["negotiation"] = {}
    if not isinstance(out["flags"], dict):
        out["flags"] = {}
    return out


def validate_state(state: dict) -> None:
    if not isinstance(state, dict) or state.get("v") != STATE_VERSION:
        raise Engine2SchemaError(f"状态版本不匹配，需要 v{STATE_VERSION}")
    for key in ("stage", "meters", "facts", "photos", "economy", "negotiation", "flags"):
        if not isinstance(state.get(key), dict):
            raise Engine2SchemaError(f"状态缺少合法字段: {key}")


def apply_patch(state: dict, patch: dict | None) -> dict:
    """Reducer：meters 深度合并；facts 整体替换（memory 单写者）；其余顶层字段整体替换。"""
    new = copy.deepcopy(state)
    if not patch:
        return new
    for key, value in patch.items():
        if key not in _TOP_KEYS or value is None:
            continue
        if key in _MERGE_KEYS and isinstance(new.get(key), dict) and isinstance(value, dict):
            merged = dict(new[key])
            merged.update(value)
            new[key] = merged
        elif isinstance(value, dict):
            new[key] = copy.deepcopy(value)
        else:
            new[key] = value
    new["meters"]["trust"] = _clamp100(new["meters"].get("trust", 10))
    new["meters"]["interest"] = _clamp100(new["meters"].get("interest", 20))
    new["meters"]["suspicion"] = _clamp100(new["meters"].get("suspicion", 0))
    facts = new.get("facts") or {}
    new["facts"] = {str(k): str(v) for k, v in list(facts.items())[:FACT_LIMIT]}
    new["v"] = STATE_VERSION
    return new


class AnalyzerOut(BaseModel):
    """感知节点结构化输出（LLM JSON 与规则降级共用同一契约）"""

    v: int = 1
    primary: str = "casual"
    intents: list[str] = Field(default_factory=list)
    tone: str = "neutral"
    suspicion_level: int = Field(default=0, ge=0, le=3)
    requests: dict[str, bool] = Field(default_factory=dict)
    observed: dict[str, bool] = Field(default_factory=dict)
    memory: list[dict[str, str]] = Field(default_factory=list)
    confidence: str = "low"

    def to_dict(self) -> dict:
        return self.model_dump()


def parse_analysis(raw: Any) -> dict | None:
    """把 LLM 的 JSON 解析为合法分析 dict；不合法返回 None（走规则降级）。"""
    if not isinstance(raw, dict):
        return None
    try:
        out = AnalyzerOut(**raw)
    except ValidationError:
        return None
    data = out.to_dict()
    data["intents"] = [i for i in data["intents"] if i in INTENTS or i == "casual"]
    if not data["intents"]:
        return None
    data["primary"] = pick_primary(data["intents"]) if data["intents"] else "casual"
    return data


def pick_primary(intents: list[str]) -> str:
    for key in INTENT_ORDER:
        if key in intents:
            return key
    return "casual"


@dataclass
class TurnContext:
    """一轮对话的只读上下文 + 回合内 scratch。节点修改状态必须经 patch。"""

    conversation_id: int
    user_id: int
    persona: Persona | None
    scenario: Scenario | None
    user_message: str
    state: dict
    history_text: str = ""
    db: Any = None
    llm: Any = None
    config: Any = None
    scratch: dict = field(default_factory=dict)
