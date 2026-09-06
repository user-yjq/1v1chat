"""v1 聊天引擎转发层（R-E4 归档后兼容层）。

实现已归档至 `_legacy/engine_v1/chat_engine.py`；本层把自身解析为该实现模块，
保留 `ENGINE_VERSION=v1` 一键回滚、parity 对照与 monkeypatch 打桩（build_llm）
的稳定导入路径，不再承载实现。
"""
import sys

from _legacy.engine_v1 import chat_engine as _impl

sys.modules[__name__] = _impl
