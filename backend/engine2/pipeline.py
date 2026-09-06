"""engine2 薄编排：会话锁 → 顺序执行节点 → patch 合并 → trace。

节点必须写成 node(ctx) -> patch（纯函数），失败语义与超时兜底见 03 架构 §10。
"""
import asyncio
import time
from typing import Any

from engine2 import ENGINE2_VERSION
from engine2.compliance import compliance as compliance_node
from engine2.defaults import pick_fallback
from engine2.nodes.actor import act
from engine2.nodes.analyzer import analyze, regex_analyze
from engine2.nodes.decider import decide
from engine2.nodes.guard import guard
from engine2.nodes.memory import memory
from engine2.schema import TurnContext, apply_patch

_NODES: list[tuple[str, Any]] = [
    ("analyze", analyze),
    ("memory", memory),
    ("decide", decide),
    ("act", act),
    ("guard", guard),
    ("compliance", compliance_node),
]

_LOCKS: dict[int, asyncio.Lock] = {}
_LOCKS_GUARD = asyncio.Lock()


async def _conversation_lock(conversation_id: int) -> asyncio.Lock:
    async with _LOCKS_GUARD:
        return _LOCKS.setdefault(conversation_id, asyncio.Lock())


async def run_turn(ctx: TurnContext) -> tuple[dict, list[dict], dict]:
    """返回 (new_state, actions, trace)。不在本函数内写 DB。"""
    lock = await _conversation_lock(ctx.conversation_id)
    async with lock:
        return await _run_unlocked(ctx)


def _timeout_s(ctx: TurnContext) -> float:
    val = getattr(ctx.config, "turn_timeout_s", 20.0)
    try:
        return float(val)
    except (TypeError, ValueError):
        return 20.0


def _fallback_action(ctx: TurnContext) -> dict:
    return {
        "kind": "reply_text",
        "content": pick_fallback(ctx.user_message),
        "content_type": "text",
        "media_url": "",
    }


async def _run_unlocked(ctx: TurnContext) -> tuple[dict, list[dict], dict]:
    state = ctx.state
    trace: dict = {
        "engine": "engine2",
        "version": ENGINE2_VERSION,
        "nodes": [],
        "llm_calls": 0,
        "decisions": {},
    }
    timeout = _timeout_s(ctx)
    actions: list[dict] = []

    for name, node in _NODES:
        started = time.perf_counter()
        ok, error = True, None
        patch: dict = {}
        try:
            patch = await asyncio.wait_for(node(ctx), timeout=timeout)
        except TimeoutError:
            ok, error = False, "timeout"
        except Exception as exc:  # noqa: BLE001 —— 节点失败不崩整轮
            ok, error = False, f"{type(exc).__name__}: {exc}"
        finally:
            if not ok and name == "analyze":
                ctx.scratch["analysis"] = regex_analyze(ctx.user_message)
            elif not ok and name == "act":
                actions.append(_fallback_action(ctx))

        node_actions = ctx.scratch.pop("actions_out", None)
        if node_actions:
            actions.extend(node_actions)
        if name == "act" and not node_actions and ok:
            actions.append(_fallback_action(ctx))

        state = apply_patch(state, patch)
        trace["nodes"].append({
            "name": name,
            "ok": ok,
            "ms": round((time.perf_counter() - started) * 1000, 1),
            "error": error,
        })
        calls = ctx.scratch.pop("llm_calls", 0)
        trace["llm_calls"] += int(calls or 0)

    if not actions:
        actions.append(_fallback_action(ctx))
    trace["decisions"] = ctx.scratch.pop("decision", {})
    trace["guard"] = ctx.scratch.pop("guard", {})
    trace["primary"] = (ctx.scratch.get("analysis") or {}).get("primary", "casual")
    compliance = ctx.scratch.pop("compliance", None)
    if compliance:
        trace["compliance"] = compliance
    return state, actions, trace
