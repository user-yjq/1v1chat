"""M4.9（R-E4）：v0.5 候选收口——默认 engine=v2、可回滚 v1、发布件对齐。"""
from pathlib import Path

from config import Settings
from version import APP_VERSION

_ROOT = Path(__file__).resolve().parents[3]


def test_default_engine_is_v2():
    s = Settings(_env_file=None)
    assert s.ENGINE_VERSION == "v2"


def test_rollback_to_v1_by_config():
    s = Settings(_env_file=None, ENGINE_VERSION="v1")
    assert s.ENGINE_VERSION == "v1"


def test_env_example_and_compose_default_v2():
    env_text = (_ROOT / ".env.example").read_text(encoding="utf-8")
    compose_text = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "ENGINE_VERSION=v2" in env_text
    assert "ENGINE_VERSION=${ENGINE_VERSION:-v2}" in compose_text


def test_release_version_is_0_5_0_and_pyproject_synced():
    import tomllib

    with open(_ROOT / "pyproject.toml", "rb") as f:
        meta = tomllib.load(f)
    assert APP_VERSION == "0.5.0"
    assert meta["project"]["version"] == APP_VERSION
