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
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True

    # JWT
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72

    # 静态媒体目录（AI 发送的照片/头像放在这里，以 /media 路由访问）
    MEDIA_DIR: str = "./media"


settings = Settings()
