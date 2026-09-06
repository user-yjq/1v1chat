"""M4 快速加固项（NFR-PROD-1 / R-C1 / R-B3 / R-E2）：prod fail-fast、版本一致、SQLite WAL。"""
import tomllib
from pathlib import Path

from config import Settings, validate_prod_settings
from db.database import make_engine
from version import APP_VERSION

_REPO_ROOT = Path(__file__).resolve().parents[3]


# --- prod fail-fast（R-C1） ------------------------------------------------ #
def test_dev_env_never_blocked():
    s = Settings(_env_file=None, APP_ENV="dev", JWT_SECRET="change-me",
                 DEEPSEEK_API_KEY="sk-placeholder", APP_DEBUG=True)
    assert validate_prod_settings(s) == []


def test_prod_placeholder_secret_and_key_flagged():
    s = Settings(_env_file=None, APP_ENV="prod", JWT_SECRET="change-me-in-production",
                 DEEPSEEK_API_KEY="sk-your-xxx", APP_DEBUG=False, LLM_MODE="auto")
    text = "; ".join(validate_prod_settings(s))
    assert "JWT_SECRET" in text
    assert "DEEPSEEK_API_KEY" in text


def test_prod_debug_flagged():
    s = Settings(_env_file=None, APP_ENV="prod", JWT_SECRET="x" * 48,
                 DEEPSEEK_API_KEY="sk-ok-1234567890", APP_DEBUG=True, LLM_MODE="auto")
    assert any("APP_DEBUG" in p for p in validate_prod_settings(s))


def test_prod_mock_llm_does_not_require_key():
    s = Settings(_env_file=None, APP_ENV="prod", JWT_SECRET="x" * 48,
                 DEEPSEEK_API_KEY="sk-placeholder", APP_DEBUG=False, LLM_MODE="mock")
    assert validate_prod_settings(s) == []


def test_prod_clean_config_passes():
    s = Settings(_env_file=None, APP_ENV="prod", JWT_SECRET="x" * 48,
                 DEEPSEEK_API_KEY="sk-prod-1234567890", APP_DEBUG=False, LLM_MODE="auto",
                 CORS_ORIGINS=["https://chat.example.com"])
    assert validate_prod_settings(s) == []


def test_prod_cors_wildcard_flagged():
    s = Settings(_env_file=None, APP_ENV="prod", JWT_SECRET="x" * 48,
                 DEEPSEEK_API_KEY="sk-prod-1234567890", APP_DEBUG=False, LLM_MODE="auto",
                 CORS_ORIGINS=["*"])
    assert any("CORS_ORIGINS" in p for p in validate_prod_settings(s))


def test_env_example_keys_match_settings_fields():
    """R-E3：.env.example 键集合必须与 config.Settings 字段全量一致（防漂移）。"""
    with open(_REPO_ROOT / ".env.example", encoding="utf-8") as f:
        example_keys = {line.split("=", 1)[0] for line in f
                        if line.strip() and not line.lstrip().startswith("#") and "=" in line}
    settings_fields = set(Settings.model_fields)
    assert example_keys == settings_fields, (
        f"缺失={sorted(settings_fields - example_keys)} 多余={sorted(example_keys - settings_fields)}"
    )


# --- 单版本源（R-E2） ------------------------------------------------------ #
def test_pyproject_version_sync_with_version_py():
    with open(_REPO_ROOT / "pyproject.toml", "rb") as f:
        meta = tomllib.load(f)
    expected = APP_VERSION.replace("-alpha", "a0")  # PEP440: 0.4.0-alpha -> 0.4.0a0
    assert meta["project"]["version"] == expected


# --- SQLite WAL / busy_timeout（R-B3，与 02 ADR-07 对齐） ------------------ #
def test_sqlite_file_engine_enables_wal_and_busy_timeout(tmp_path):
    url = f"sqlite:///{tmp_path / 'wal_test.db'}"
    engine = make_engine(url)
    try:
        with engine.connect() as conn:
            journal = conn.exec_driver_sql("PRAGMA journal_mode").fetchone()[0]
            busy = int(conn.exec_driver_sql("PRAGMA busy_timeout").fetchone()[0])
        assert str(journal).lower() == "wal"
        assert busy == 5000
    finally:
        engine.dispose()
