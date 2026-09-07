"""
LLM Provider（方案 C：单次生成）
- RemoteLLM：DeepSeek / OpenAI 兼容 chat/completions
- MockLLM：离线确定性假回复（LLM_MODE=mock 或未配置有效 key），供开发与测试验收
- build_llm()：按配置选择，engine 只依赖 generate(system, user) -> str
"""
import hashlib
import json
import threading
import time

import httpx
from config import settings
from core import metrics
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class BaseLLM:
    async def generate(self, system: str, user: str) -> str:
        raise NotImplementedError

    async def extract_json(self, system: str, user: str) -> dict | None:
        """结构化输出；不可用时返回 None（调用方走规则降级）。"""
        return None


async def _record_llm_call(kind: str, coro):
    """LLM 调用计时打点（M4.5 R-D2）：成功/失败都计数，异常原样上抛。"""
    started = time.perf_counter()
    try:
        result = await coro
        metrics.record_llm_call(kind, time.perf_counter() - started, ok=True)
        return result
    except Exception:
        metrics.record_llm_call(kind, time.perf_counter() - started, ok=False)
        raise


class MockLLM(BaseLLM):
    """离线确定性回复，保证无 AI 味；仅用于无 key 的开发/验收"""

    _lines = [
        "嗯嗯，我懂你说的～那你呢，平时这个点都在干嘛呀",
        "哈哈哈真的假的，你别逗我",
        "哦哦这样啊，我还以为你在忙呢，都没敢打扰你",
        "是吧是吧！我也觉得，那天我跟朋友说起这事她还笑我",
        "那可不，过日子嘛，不就是这些小事堆起来的",
        "唉 我这两天也有点累，不过跟你唠两句感觉好多了",
        "行行行，你继续说，我听着呢",
    ]

    async def generate(self, system: str, user: str) -> str:
        h = hashlib.md5((system + user).encode("utf-8")).hexdigest()
        idx = int(h[:4], 16) % len(self._lines)
        text = self._lines[idx]
        metrics.record_llm_call("chat", 0.0, ok=True)
        return text

    # extract_json 继承 BaseLLM：返回 None → Analyzer 走规则降级


class LLMCircuitOpenError(RuntimeError):
    """上游熔断打开（R-A2）：本轮直接走引擎降级话术，不再发起网络调用。"""


class LLMBudgetExceededError(RuntimeError):
    """全局并发预算不足（R-A2）：本轮直接降级，避免请求堆积压垮上游。"""


# 熔断状态机（进程内单例；asyncio 单线程 + 锁兜底多线程）
_state = {"mode": "closed", "failures": 0, "open_until": 0.0}
_state_lock = threading.Lock()
_inflight = 0
_inflight_lock = threading.Lock()


def _now_s() -> float:
    return time.monotonic()


def _threshold() -> int:
    try:
        return max(1, int(getattr(settings, "LLM_CIRCUIT_FAIL_THRESHOLD", 3)))
    except (TypeError, ValueError):
        return 3


def _cooldown_s() -> float:
    try:
        return max(0.0, float(getattr(settings, "LLM_CIRCUIT_COOLDOWN_S", 30.0)))
    except (TypeError, ValueError):
        return 30.0


def reset_llm_guards() -> None:
    """测试用：清空熔断状态与并发计数器。"""
    global _inflight
    with _state_lock:
        _state.update({"mode": "closed", "failures": 0, "open_until": 0.0})
    with _inflight_lock:
        _inflight = 0


def _breaker_precheck() -> LLMCircuitOpenError | None:
    """放行返回 None；熔断窗口内返回异常（并计 rejected）。"""
    with _state_lock:
        if _state["mode"] == "open" and _now_s() < _state["open_until"]:
            metrics.record_circuit("rejected")
            return LLMCircuitOpenError("LLM 上游熔断中，本轮降级")
        if _state["mode"] == "open":
            # 冷却结束 → 半开：放行探活请求
            _state["mode"] = "half_open"
    return None


def _breaker_report(ok: bool) -> None:
    """按调用结果推进状态机：closed 计连续失败；half_open 探活成败闭环。"""
    with _state_lock:
        if _state["mode"] == "half_open":
            if ok:
                _state["mode"] = "closed"
                _state["failures"] = 0
                metrics.record_circuit("closed")
            else:
                _state["mode"] = "open"
                _state["open_until"] = _now_s() + _cooldown_s()
                metrics.record_circuit("opened")
            return
        if ok:
            _state["failures"] = 0
            return
        _state["failures"] += 1
        if _state["failures"] >= _threshold():
            _state["mode"] = "open"
            _state["open_until"] = _now_s() + _cooldown_s()
            metrics.record_circuit("opened")
            _state["failures"] = 0


class _LlmBudget:
    """全局并发预算护栏：限制同时进行的 LLM 请求数（默认 8）。

    用计数而非 asyncio.Semaphore：检查与自增之间无 await，天然原子；
    超出上限立即抛预算异常（不排队），由引擎走降级话术。
    """

    def __init__(self) -> None:
        self._acquired = False

    async def __aenter__(self):
        global _inflight
        limit = max(1, int(getattr(settings, "LLM_MAX_CONCURRENCY", 8)))
        with _inflight_lock:
            if _inflight >= limit:
                metrics.record_circuit("rejected")
                raise LLMBudgetExceededError("LLM 并发预算不足，本轮降级")
            _inflight += 1
        self._acquired = True
        return self

    async def __aexit__(self, *exc_info):
        global _inflight
        if self._acquired:
            with _inflight_lock:
                _inflight -= 1
        return False


class RemoteLLM(BaseLLM):
    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.95,
                 max_tokens: int = 300, timeout: float = 30.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _post(self, payload: dict) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        return (data["choices"][0]["message"]["content"] or "").strip()

    async def generate(self, system: str, user: str) -> str:
        """单次生成：熔断预检 → 并发预算 → 计时调用 → 结果回报状态机。"""
        pre = _breaker_precheck()
        if pre is not None:
            raise pre
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        try:
            async with _LlmBudget():
                result = await _record_llm_call("chat", self._post(payload))
        except (LLMCircuitOpenError, LLMBudgetExceededError):
            raise
        except Exception:
            _breaker_report(ok=False)
            raise
        _breaker_report(ok=True)
        return result

    async def extract_json(self, system: str, user: str) -> dict | None:
        """尝试 JSON 模式结构化输出；解析失败一律返回 None（不抛异常）。"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": 800,
            "stream": False,
        }
        pre = _breaker_precheck()
        if pre is not None:
            return None
        started = time.perf_counter()
        try:
            async with _LlmBudget():
                content = await self._post(payload)
        except (LLMCircuitOpenError, LLMBudgetExceededError):
            return None
        except Exception:
            metrics.record_llm_call("json", time.perf_counter() - started, ok=False)
            _breaker_report(ok=False)
            return None
        metrics.record_llm_call("json", time.perf_counter() - started, ok=True)
        _breaker_report(ok=True)
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(content[start:end + 1])
        except (json.JSONDecodeError, ValueError):
            return None


def build_llm() -> BaseLLM:
    """auto：key 有效走真实模型；mock：离线假回复"""
    mode = (settings.LLM_MODE or "auto").strip().lower()
    key = (settings.DEEPSEEK_API_KEY or "").strip()
    if mode == "mock" or not key or key == "sk-placeholder" or key.startswith("sk-your"):
        return MockLLM()
    return RemoteLLM(
        api_key=key,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
    )


def is_mock_llm() -> bool:
    return isinstance(build_llm(), MockLLM)


def llm_config_report() -> dict:
    """readiness 上游配置探测（R-D4）：mode/真实 key 是否就绪；不发起真实网络调用。"""
    mode = (settings.LLM_MODE or "auto").strip().lower()
    key = (settings.DEEPSEEK_API_KEY or "").strip()
    if mode == "mock":
        return {"mode": mode, "ready": True, "detail": "LLM_MODE=mock（离线确定性回复）", "model": "mock"}
    if key and key != "sk-placeholder" and not key.startswith("sk-your"):
        return {"mode": mode, "ready": True, "detail": "DEEPSEEK_API_KEY 已配置", "model": settings.DEEPSEEK_MODEL}
    return {
        "mode": mode,
        "ready": False,
        "detail": f"LLM_MODE={mode} 但 DEEPSEEK_API_KEY 缺失或为占位，实际将回退 MockLLM",
        "model": "mock",
    }
