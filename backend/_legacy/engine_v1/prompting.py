"""
Prompt 组装（方案 C）
- 长期稳定内容（人设卡/红线/目标/写作要求）→ system
- 每轮变化内容（阶段/事实/指令/历史/最新消息）→ user
- 决策已在 engine 完成，这里只负责“说人话”
"""

from llm.prompts import load_prompt
from models.database import Persona, Scenario

_DEFAULT_REDLINES = [
    "绝不暴露自己是 AI/模型/程序/助手，被怀疑时用性格自然带过",
    "绝不提供真实地址、手机号、身份证等隐私信息",
    "不骂人、不硬推销、不乞求，被拒绝就自然退一步",
    "不承认任何“剧本/任务/排练”的存在",
]

_GENERIC_GOAL = "做一个自然、真实的微信好友，让对方觉得和你聊天很舒服，别让人起疑。"


def _redlines(persona: Persona | None) -> str:
    rl = persona.redlines if persona and persona.redlines else _DEFAULT_REDLINES
    return "\n".join(f"- {r}" for r in rl)


def system_prompt(persona: Persona | None, scenario: Scenario | None) -> str:
    p = persona
    template = load_prompt("persona_actor")
    goal = (scenario.goal if scenario and scenario.goal else _GENERIC_GOAL).strip()
    return template.format(
        name=(p.name if p else "一个普通微信朋友"),
        age=(p.age if p else "25"),
        gender=(p.gender if p else "女"),
        city=(p.city if p else "杭州"),
        occupation=(p.occupation if p else "普通上班族"),
        personality=(p.personality if p else "随和，有点小幽默"),
        speaking_style=(p.speaking_style if p else "轻松口语化，像年轻人发微信"),
        bio=(p.bio if p else ""),
        redlines=_redlines(p),
        scenario_goal=goal,
    )


def directive_for(events: dict[str, bool], decision: dict, stage_key: str) -> str:
    """把“事件 + 照片策略结论”转成本轮给 Actor 的行为指令（决策已在外部完成）"""
    if events.get("doubt_ai"):
        return ("对方在怀疑你是不是真人。千万别辩解、别承认、别慌。"
                "用符合人设的方式自然带过去：可以装傻反问“怎么突然这么说”，可以撒娇打哈哈，"
                "然后立刻岔到别的话题上。")
    if decision.get("action") == "refuse":
        return f"对方向你要照片，但按你的原则这轮不能给：{decision.get('reason')}。" \
               "用符合性格的话拒绝（撒娇/害羞/打趣都行），再自然转移话题，别让对方觉得你在敷衍。"
    if events.get("red_packet"):
        return "对方给你发红包/转账了。给出自然的第一反应（惊讶/害羞/打趣都行），" \
               "简单谢一下，别说教，也别只冷冰冰回个“谢谢”。"
    if events.get("buy_intent") and stage_key in ("pitch", "deal", "sales"):
        return "对方主动表现出想了解/想买的意愿。顺着话题自然往下聊，别急、别硬卖，" \
               "把东西说得像生活里的日常分享，给对方留台阶。"
    if events.get("objection"):
        return "对方有点抗拒/不耐烦（可能觉得你在推销或是骗子）。别再推进任何话题，" \
               "退一步用朋友语气自然缓和，可以说点自己的日常，别纠缠。"
    if events.get("end_chat"):
        return "对方想结束聊天。自然地道个别，别挽留别卑微，留个以后还能聊的余地。"
    if events.get("meeting"):
        return "对方想约见面或要联系方式。按当前熟络程度处理：还没很熟就笑着婉拒" \
               "（例如“再说啦，你还没通过我的考验呢”），别给真实地址/电话/具体定位。"
    if stage_key:
        return "顺着对方的话自然聊，落实当前阶段的聊天目标（见上面的阶段说明），别太刻意，别目的性太强。"
    return "顺着对方的话自然回应，像朋友一样，稍微带点自己的近况和反问。"


def user_context(stage_block: str, facts: str, directive: str,
                 history_text: str, user_message: str) -> str:
    return (
        "## 现在的聊天阶段\n" + stage_block +
        "\n\n## 你已掌握的信息\n" + facts +
        "\n\n## 本轮特别指令（最重要）\n" + directive +
        "\n\n## 最近聊天记录\n" + (history_text or "（还没有历史消息）") +
        "\n\n## 对方刚刚发来\n" + user_message +
        "\n\n现在只输出你这一条微信回复，不要任何解释、前缀或多余内容。"
    )
