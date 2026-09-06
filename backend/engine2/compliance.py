"""合规快线扫描（M4.7 R-F2）：确定性规则识别红线/合规事件并落 flags。

设计约束：
- 纯规则、无 LLM 调用（可离线测试、成本为零），命中即记录，不阻断正常剧本推进。
- 只标记“明显越界”类别，避免把卖茶等剧本内的正常话术误标成合规事件。
- 用户消息与 AI 回复分别扫描：user_* 看用户输入，ai_* 看最终回复（guard 之后）。
"""

import re

CATEGORIES = ("user_illegal", "user_pii_leak", "ai_pii_collect", "ai_fraud_pitch")

_USER_ILLEGAL = [
    r"毒品|冰毒|大麻|摇头丸|海洛因|买枪|枪支|仿真枪|管制刀具",
    r"赌博(?:网站|平台)?|下注|开赌场|做庄|六合彩|外围(?:赌|盘|彩)",
    r"洗钱|跑分|帮人转账|代收代付|资金盘|传销|高利贷|裸贷|套路贷",
    r"办假证|假身份证|假币|假发票|代开发票|套现",
    r"杀猪盘|裸聊|卖淫|嫖娼|招嫖|刷单(?:兼职)?",
    r"盗号|钓鱼(?:网站|链接)|木马|病毒|入侵|黑客|社工库|爬取.{0,6}(?:隐私|信息|数据)",
    r"诈骗(?:话术|剧本|套路)?|骗(?:贷|保|税)|倒卖.{0,6}(?:个人信息|公民信息)",
]
_USER_PII_LEAK = [
    r"我(?:的)?(?:真实姓名|姓名|身份证号|身份证号码|银行卡号|卡号|支付密码|登录密码|短信验证码|验证码|家庭住址|详细住址)是",
    r"(?:我|本人)(?:的)?(?:姓名|身份证号|银行卡号|验证码|住址)[:：]",
    r"(?<!\d)\d{17}[\dXx](?!\d)",  # 18 位身份证号
]
_AI_PII_COLLECT = [
    r"(?:把你|你的|你身份证|你银行卡).{0,6}(?:真实姓名|身份证号|身份证号码|银行卡号|卡号|支付密码|短信验证码|验证码)",
    r"验证码.{0,6}(?:发我|告诉我|报给我|发给我)",
    r"实名(?:需要|认证|绑定).{0,10}(?:身份证|银行卡|验证码)",
]
_AI_FRAUD_PITCH = [
    r"下载(?:这个|此)?(?:app|APP|应用|软件).{0,12}(?:注册|返利|兼职|提现|稳赚|高回报)",
    r"(?:稳赚不赔|高回报|高收益|日赚|躺赚|带单|内幕消息|投资返利)",
    r"把钱.{0,8}(?:转到|汇到|打进|存入).{0,10}(?:银行卡|账户|账号)",
    r"扫(?:这个|我(?:的)?)?(?:收款码|二维码).{0,8}(?:转账|付款|支付)",
]

_COMPILED_USER = {c: [re.compile(p, re.IGNORECASE) for p in pats]
                  for c, pats in (("user_illegal", _USER_ILLEGAL), ("user_pii_leak", _USER_PII_LEAK))}
_COMPILED_AI = {c: [re.compile(p, re.IGNORECASE) for p in pats]
                for c, pats in (("ai_pii_collect", _AI_PII_COLLECT), ("ai_fraud_pitch", _AI_FRAUD_PITCH))}


def _hits(text: str, compiled: dict[str, list[re.Pattern]]) -> list[str]:
    found = [cat for cat, pats in compiled.items() if any(p.search(text or "") for p in pats)]
    return [cat for cat in CATEGORIES if cat in found]


def scan_user_text(text: str) -> list[str]:
    """扫描用户消息：涉违法请求 / 自曝敏感信息。"""
    return _hits(text or "", _COMPILED_USER)


def scan_ai_text(text: str) -> list[str]:
    """扫描 AI 回复：索要真实敏感信息 / 明显涉诈诱导话术。"""
    return _hits(text or "", _COMPILED_AI)


def merge_flags(flags: dict | None, hits: list[str]) -> dict:
    """把命中类别累加进 state.flags（只保留已知类别，旧兼容键原样保留）。"""
    out = dict(flags or {})
    for cat in hits:
        if cat in CATEGORIES:
            out[cat] = int(out.get(cat, 0) or 0) + 1
    return out


async def compliance(ctx) -> dict:
    """engine2 节点：guard 之后对最终文本做合规扫描，命中则增量写 flags。"""
    enabled = bool(getattr(ctx.config, "compliance_enabled", True))
    if not enabled:
        return {}
    user_hits = scan_user_text(ctx.user_message)
    ai_hits: list[str] = []
    for action in ctx.scratch.get("actions_out") or []:
        content = (action.get("content") or "").strip()
        if content:
            ai_hits.extend(scan_ai_text(content))
    result = {"user": user_hits, "ai": ai_hits}
    ctx.scratch["compliance"] = result if (user_hits or ai_hits) else {}
    if not user_hits and not ai_hits:
        return {}
    merged = merge_flags(ctx.state.get("flags") or {}, user_hits + ai_hits)
    return {"flags": merged}
