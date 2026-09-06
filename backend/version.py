"""版本单一来源（R-E2 / NFR-PROD 一致性）。

运行时显示版本一律引用 APP_VERSION；根 pyproject.toml 的 PEP440 版本
由 tests/engine2_core/test_prod_safety.py 校验与本值保持一致。
"""
APP_VERSION = "0.5.0"
