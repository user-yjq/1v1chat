"""
应用配置（方案 C）
环境变量读取：.env / 系统环境
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # DeepSeek / OpenAI 兼容接口
    DEEPSEEK_API_KEY: str = "sk-placeholder"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # LLM 运行模式：auto=有 key 就真调，mock=离线假回复（开发/测试用）
    LLM_MODE: str = "auto"

    # 数据库
    DATABASE_URL: str = "sqlite:///./data/1v1chat.db"

    # 应用
    APP_ENV: str = "dev"            # dev / prod（prod 触发 fail-fast 校验，见 validate_prod_settings）
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True

    # JWT
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72

    # 静态媒体目录（AI 发送的照片/头像放在这里，以 /media 路由访问）
    MEDIA_DIR: str = "./media"

    # CORS 白名单（T-13：禁止 * + credentials 组合；为空则回退 ["*"]）
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # === engine2（v0.3 起）===
    ENGINE_VERSION: str = "v1"          # v1=旧引擎 / v2=engine2
    TURN_TIMEOUT_S: float = 20.0
    ACTOR_MAX_TOKENS: int = 120
    ACTOR_TEMPERATURE: float = 0.9
    HISTORY_LIMIT: int = 10
    ANALYZER_MODEL: str = ""            # 空则复用 DEEPSEEK_MODEL
    GUARD_ENABLED: bool = True
    GUARD_SAMPLE_RATE: float = 0.05
    MSG_MAX_LEN: int = 2000
    CHAT_RATE_PER_MIN: int = 30
    STATE_FACTS_MAX: int = 20


settings = Settings()

# 生产安全默认值校验（R-C1 / NFR-PROD-1：占位凭据不允许上线）
_PLACEHOLDER_JWT = {"change-me", "change-me-in-production"}
_PLACEHOLDER_KEY_PREFIXES = ("sk-placeholder", "sk-your")


def validate_prod_settings(cfg: Settings | None = None) -> list[str]:
    """APP_ENV=prod 时做 fail-fast 校验；返回问题列表（空列表 = 通过）。

    非 prod 环境不做检查，保证开发/测试启动不被拦。
    """
    c = cfg or settings
    if c.APP_ENV != "prod":
        return []
    problems: list[str] = []
    jwt = (c.JWT_SECRET or "").strip()
    if not jwt or jwt.lower() in _PLACEHOLDER_JWT or jwt.lower().startswith("change"):
        problems.append("JWT_SECRET 仍是占位/默认值，prod 必须显式设置强随机 secret")
    if (c.LLM_MODE or "").strip().lower() != "mock":
        key = (c.DEEPSEEK_API_KEY or "").strip()
        if not key or key.lower() in _PLACEHOLDER_JWT or key.lower().startswith(_PLACEHOLDER_KEY_PREFIXES):
            problems.append("DEEPSEEK_API_KEY 缺失或为占位值，prod 必须显式设置真实 key（或显式 LLM_MODE=mock）")
    if bool(c.APP_DEBUG):
        problems.append("APP_DEBUG=True 不应在生产开启")
    return problems
