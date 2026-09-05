"""决策节点：心理计分 → 阶段推进 → 照片谈判 → 战术路由。纯决策，不调用 LLM。"""
from copy import deepcopy

from engine2.policies import (
    decide_stage_advance,
    negotiate_photo,
    update_meters,
)
from engine2.tactics import build_directive, route


async def decide(ctx) -> dict:
    analysis = ctx.scratch.get("analysis") or {"intents": ["casual"], "observed": {}}
    intents = set(analysis.get("intents") or [])
    observed = analysis.get("observed") or {}

    stage = dict(ctx.state["stage"])
    stage["turns"] = int(stage.get("turns", 0)) + 1
    pre_state = dict(ctx.state)
    pre_state["stage"] = stage

    stages = list(ctx.scenario.stages) if ctx.scenario and ctx.scenario.stages else []
    idx_before = max(0, min(int(ctx.state["stage"]["idx"]), len(stages) - 1)) if stages else 0
    key_before = stages[idx_before].get("key", "") if stages else ""

    idx, advanced = decide_stage_advance(ctx.scenario, pre_state, analysis)
    new_stage = {
        "scenario_slug": stage.get("scenario_slug"),
        "idx": idx,
        "turns": 0 if advanced else stage["turns"],
    }

    meters = update_meters(ctx.state, analysis)

    photos = deepcopy(ctx.state["photos"])
    if "request_photo" in intents:
        photos["asked"] = int(photos.get("asked", 0)) + 1
    economy = deepcopy(ctx.state["economy"])
    if observed.get("sent_redpacket"):
        economy["red_packets"] = int(economy.get("red_packets", 0)) + 1
    negotiation = deepcopy(ctx.state.get("negotiation") or {})
    if "buy_intent" in intents:
        negotiation["last_pitch_round"] = stage["turns"]

    # 照片谈判基于“本回合到达时的阶段”（推进前），避免到达即放行
    photo = negotiate_photo(ctx.persona, ctx.state, key_before, analysis)
    if photo.get("action") == "refuse":
        photos["refused"] = int(photos.get("refused", 0)) + 1
    if photo.get("action") == "send" and ctx.persona:
        photos["sent"] = int(photos.get("sent", 0)) + 1

    tactic = route(analysis, key_before)
    directive = build_directive(tactic, photo)
    ctx.scratch["directive"] = directive
    ctx.scratch["tactic_key"] = tactic.key
    ctx.scratch["photo_decision"] = photo
    ctx.scratch["narrative"] = {
        **pre_state,
        "stage": {"scenario_slug": stage.get("scenario_slug"), "idx": idx_before,
                  "turns": stage["turns"]},
    }
    ctx.scratch["decision"] = {
        "stage_advanced": advanced,
        "stage_key": key_before,
        "tactic": tactic.key,
        "photo": photo.get("action"),
    }

    return {
        "stage": new_stage,
        "meters": meters,
        "photos": photos,
        "economy": economy,
        "negotiation": negotiation,
    }
