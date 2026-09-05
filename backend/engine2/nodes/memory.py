"""记忆节点：抽取用户事实写入 facts。隐私忽略：手机/地址/证件等不落库。"""
import re

from engine2.schema import FACT_LIMIT

_SENSITIVE = re.compile(
    r"手机|电话|身份证|银行卡|卡号|密码|地址|门牌|住址|微信号|银行|账号|验证码",
    re.IGNORECASE,
)
_PATTERNS = [
    (re.compile(r"我(?:在|住在|呆在)([\u4e00-\u9fff]{2,8}?)(?:上班|工作)"), "work_city"),
    (re.compile(r"我(?:是|做|干|从事)([\u4e00-\u9fff]{2,10}?)(?:工作|职业|这一行|的)"), "job"),
    (re.compile(r"养了(?:一只|一个|只|条|个)?([\u4e00-\u9fff]{1,5}?)(?:[，。,.!！\s]|$)"), "pet"),
    (re.compile(r"我今年(\d{1,3})岁"), "age"),
]


def extract_facts(text: str) -> dict:
    """确定性抽取（规则版）。LLM 提供的记忆由 LLM 分析合并后在这里统一清洗。"""
    facts: dict[str, str] = {}
    if _SENSITIVE.search(text):
        return facts
    for pat, attr in _PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        value = re.sub(r"\s+", "", m.group(1))[:24]
        if value and attr not in facts:
            facts[attr] = value
    return facts


def _safe_value(text: str) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r"\s+", "", text)[:40]
    if _SENSITIVE.search(cleaned):
        return None
    return cleaned


async def memory(ctx) -> dict:
    analysis = ctx.scratch.get("analysis") or {}
    facts = extract_facts(ctx.user_message)
    for item in analysis.get("memory") or []:
        if not isinstance(item, dict):
            continue
        attr = str(item.get("attr", "")).strip().lower()[:24]
        value = _safe_value(str(item.get("value", "")))
        if attr and value and not attr.startswith("_"):
            facts[attr] = value
    limit = getattr(ctx.config, "state_facts_max", FACT_LIMIT)
    # facts 由本节点整表重算后整体替换（apply_patch 不合并 facts）
    merged = dict(ctx.state.get("facts") or {})
    merged.update(facts)
    keys = list(merged)
    for key in keys[:max(0, len(keys) - limit)]:
        del merged[key]
    ctx.scratch["memory_extracted"] = list(merged.keys())
    return {"facts": merged}
