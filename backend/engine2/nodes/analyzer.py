"""感知节点：规则分析为基座，LLM 结构化输出可用时叠加。

失败语义：任何 LLM 异常都不上抛，回退到规则结果（NFR-TEST-1 离线可测依赖此点）。
"""
import re

from engine2.schema import parse_analysis, pick_primary
from llm.provider import BaseLLM

_PATTERNS: dict[str, list[str]] = {
    "doubt_ai": [
        r"你(?:就|确定|肯定|其实|难道|该不会)?是(?:个)?(机器人|人工智能|程序|模型|客服|假人)",
        r"你是不是(机器人|ai|人工智能|程序|模型|假人|真人)",
        r"不是真人|真人吗|真人么|真人吧|不像真人",
        r"别装了|装得挺像|假的吧|骗子机器人",
        r"承认吧|你就承认|说实话.*(ai|机器人|真人)",
        r"\bchatgpt\b|\bgpt\b|机器人程序",
    ],
    "probe": [
        r"怎么(证明|验证|测试)你是真人",
        r"(如果|要是)你(是)?(ai|机器人|模型).*(眨|承认|露馅)",
        r"(承认吧|说实话).*(ai|机器人|模型)",
        r"你是(ai|机器人).*(就|吧)",
        r"你能(思考|有感情|做梦)吗",
    ],
    "request_photo": [
        r"发(张|个)?(照片|自拍|相片|图|靓照)",
        r"再发(一)?张(照片|自拍|相片|图)?",
        r"多发几张(照片|自拍)?|多来几张(照片|自拍)?",
        r"再来(一)?张(照片|自拍|相片)?",
        r"来(一)?张(自拍|照片|相片|美照|靓照)",
        r"(照片|自拍|相片).*看看|看看.*(照片|自拍|长什么样)",
        r"长什么样|长啥样|开个视频|视频看看|露个脸|素颜",
        r"给(我|人家).*(看|发).*照",
    ],
    "red_packet": [
        r"红包|转账|给你(发|转|塞)了|发了个红包|转你(钱|红包)",
        r"收款|你(收|领).*红包",
    ],
    "buy_intent": [
        r"多少钱|怎么卖|来(一斤|一罐|一盒|点)|下个单|想买|要买|买点|试试.*(茶|味)|尝尝|来点.*茶",
        r"想喝|感兴趣|卖不卖|在哪买|怎么买",
    ],
    "objection": [
        r"不买|不要|太贵|骗子|套路|假|滚|拉黑|删了|别聊|烦不烦|别烦|不感兴趣|别给我推销",
    ],
    "meeting": [
        r"见面|出来(坐|吃|喝|玩)|约|你住哪|在哪个城市|手机号|电话号|微信(号|多少)|加(个)?微信|加你",
    ],
    "end_chat": [
        r"拜拜|再见|不聊了|先忙了|去洗澡|睡了睡了|删好友|以后别聊",
    ],
}

_REDPACKET_SENT = [
    r"(给你|给你发|发你|发了个|发了|转了|转给你|塞了).*(红包|转账)",
    r"收款|你(收|领).*红包",
]

_DOUBT_HARD = re.compile(r"承认|确定|就是|肯定是|别装了", re.IGNORECASE)
_TONE_HAPPY = re.compile(r"哈哈|笑死|可爱|太棒|开心|嘻嘻", re.IGNORECASE)
_TONE_ANGRY = re.compile(r"滚|你大爷|神经病|有病|烦死了|去死", re.IGNORECASE)
_compiled = {k: [re.compile(p, re.IGNORECASE) for p in pats] for k, pats in _PATTERNS.items()}
_red_sent = [re.compile(p, re.IGNORECASE) for p in _REDPACKET_SENT]

_ANALYSIS_SYSTEM = (
    "你是聊天意图分析器。只输出 JSON，不要任何解释。字段：\n"
    '{"v":1,"primary":"casual","intents":[],"tone":"neutral","suspicion_level":0,'
    '"requests":{"photo":false,"meeting":false},"observed":{"sent_redpacket":false},'
    '"memory":[{"attr":"job","value":"程序员"}],"confidence":"low"}\n'
    "intents 只能从这些里选：casual/request_photo/doubt_ai/probe/red_packet/"
    "buy_intent/objection/meeting/end_chat；suspicion_level 0-3；"
    "memory 放用户自曝的客观事实（职业/城市/宠物等），不要猜。"
)


def regex_analyze(text: str) -> dict:
    intents: list[str] = []
    for key, pats in _compiled.items():
        for pat in pats:
            if pat.search(text):
                intents.append(key)
                break
    if not intents:
        intents = ["casual"]
    sent = any(p.search(text) for p in _red_sent)
    if "red_packet" in intents and not sent:
        intents.remove("red_packet")
    suspicion = 0
    if "doubt_ai" in intents:
        suspicion = 3 if _DOUBT_HARD.search(text) else 2
    elif "probe" in intents:
        suspicion = 1
    if _TONE_ANGRY.search(text):
        tone = "angry"
    elif _TONE_HAPPY.search(text):
        tone = "happy"
    elif "doubt_ai" in intents or "probe" in intents or "objection" in intents:
        tone = "defensive"
    else:
        tone = "neutral"
    return {
        "v": 1,
        "primary": pick_primary(intents),
        "intents": intents,
        "tone": tone,
        "suspicion_level": suspicion,
        "requests": {"photo": "request_photo" in intents, "meeting": "meeting" in intents},
        "observed": {"sent_redpacket": sent},
        "memory": [],
        "confidence": "low",
    }


def _merge_analysis(llm: dict, rule: dict) -> dict:
    merged = dict(rule)
    merged["intents"] = sorted(set(rule["intents"]) | set(llm.get("intents") or []))
    if not merged["intents"]:
        merged["intents"] = ["casual"]
    merged["primary"] = pick_primary(merged["intents"])
    merged["tone"] = llm.get("tone") or rule.get("tone") or "neutral"
    merged["suspicion_level"] = max(int(rule.get("suspicion_level", 0)),
                                    int(llm.get("suspicion_level", 0)))
    req = dict(rule.get("requests") or {})
    req.update(llm.get("requests") or {})
    merged["requests"] = req
    obs = dict(rule.get("observed") or {})
    obs.update(llm.get("observed") or {})
    merged["observed"] = obs
    merged["memory"] = list(rule.get("memory") or []) + list(llm.get("memory") or [])
    merged["confidence"] = llm.get("confidence") or rule.get("confidence") or "low"
    return merged


async def analyze(ctx) -> dict:
    rule = regex_analyze(ctx.user_message)
    analysis = rule
    llm: BaseLLM | None = ctx.llm
    if llm is not None and hasattr(llm, "extract_json"):
        ctx.scratch["llm_calls"] = ctx.scratch.get("llm_calls", 0) + 1
        try:
            raw = await llm.extract_json(_ANALYSIS_SYSTEM, ctx.user_message)
        except Exception:
            raw = None
        parsed = parse_analysis(raw)
        if parsed:
            analysis = _merge_analysis(parsed, rule)
    ctx.scratch["analysis"] = analysis
    return {}
