"""engine2 异常层级"""


class Engine2Error(Exception):
    """引擎 v2 领域异常基类"""


class Engine2SchemaError(Engine2Error):
    """状态/schema 校验失败"""


class Engine2StateError(Engine2Error):
    """状态非法（越权、阶段越界等）"""
