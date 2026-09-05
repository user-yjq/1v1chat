"""
事件识别（规则级，方案 C）
只关心推动剧本/照片策略需要的几类信号，覆盖：
doubt_ai / request_photo / red_packet / buy_intent / objection / meeting / end_chat
"""
import re

_PATTERNS: dict[str, list[str]] = {
    "doubt_ai": [
        r"是(机器人|ai|人工智能|程序|模型|客服)",
        r"机器人|人工智能|不是真人|真人吗|真人么",
        r"别装了|装得挺像|假的吧|骗子机器人",
        r"\bgpt\b|chatgpt|\bai\b",
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

_compiled = {k: [re.compile(p, re.IGNORECASE) for p in pats] for k, pats in _PATTERNS.items()}


def detect_events(text: str) -> dict[str, bool]:
    """返回事件是否命中（可多事件同时命中）"""
    out = {k: False for k in _PATTERNS}
    for key, pats in _compiled.items():
        for pat in pats:
            if pat.search(text):
                out[key] = True
                break
    return out


def primary_event(events: dict[str, bool]) -> str:
    """按重要度返回最主要事件，用于 trace / 调试"""
    order = ["doubt_ai", "request_photo", "red_packet", "buy_intent", "objection", "end_chat", "meeting"]
    for k in order:
        if events.get(k):
            return k
    return "casual"
