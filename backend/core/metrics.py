"""进程内运行指标（M4.5 R-D2）：计数器 + Prometheus 文本暴露，无第三方依赖。

覆盖：LLM 调用量/延迟/失败、Guard 拦截/重写/兜底/抽样、HTTP 请求量/耗时。
多 worker 时每个进程独立计数，由 /api/metrics 各拉一份（跨进程聚合属观测平台职责）。
"""
import threading

_LOCK = threading.Lock()
_llm_calls: dict[str, int] = {}
_llm_failed: dict[str, int] = {}
_llm_latency_sum: dict[str, float] = {}
_llm_latency_count: dict[str, int] = {}
_guard: dict[str, int] = {}
_http_total: dict[str, int] = {}
_http_dur_sum: dict[str, float] = {}
_http_count: dict[str, int] = {}


def reset() -> None:
    """清空全部计数（测试用）。"""
    with _LOCK:
        _llm_calls.clear()
        _llm_failed.clear()
        _llm_latency_sum.clear()
        _llm_latency_count.clear()
        _guard.clear()
        _http_total.clear()
        _http_dur_sum.clear()
        _http_count.clear()


def _bump(d: dict, key: str, n: float | int = 1) -> None:
    d[key] = d.get(key, 0) + n


def record_llm_call(kind: str, seconds: float, ok: bool) -> None:
    """记录一次 LLM 调用：kind=chat/json（analyzer/actor/guard 共用）。"""
    with _LOCK:
        _bump(_llm_calls, kind)
        if not ok:
            _bump(_llm_failed, kind)
        _bump(_llm_latency_sum, kind, seconds)
        _bump(_llm_latency_count, kind)


def record_guard(*, blocked: bool = False, rewrote: bool = False,
                 fallback: bool = False, sampled: bool = False) -> None:
    """Guard 事件计数（每轮按命中标志累加一次）。"""
    with _LOCK:
        if blocked:
            _bump(_guard, "blocked")
        if rewrote:
            _bump(_guard, "rewrote")
        if fallback:
            _bump(_guard, "fallback")
        if sampled:
            _bump(_guard, "sampled")


def record_http(method: str, status: int, seconds: float) -> None:
    key = f"{method}|{status}"
    with _LOCK:
        _bump(_http_total, key)
        _bump(_http_dur_sum, key, seconds)
        _bump(_http_count, key)


def _metric_lines(metric: str, doc: str, kind: str, data: dict, seconds: bool = False) -> list[str]:
    lines = [f"# TYPE {metric} {kind}", f"# HELP {metric} {doc}"]
    for key in sorted(data):
        val = data[key]
        lines.append(f"{metric}{{kind=\"{key}\"}} "
                     + (f"{float(val):.6f}" if seconds else str(int(val))))
    return lines


def render() -> str:
    """Prometheus 文本格式快照（metrics endpoint 用）。"""
    out: list[str] = []
    with _LOCK:
        out += _metric_lines("chat_llm_calls_total", "LLM 调用次数", "counter", _llm_calls)
        out += _metric_lines("chat_llm_calls_failed_total", "LLM 调用失败次数", "counter", _llm_failed)
        out += _metric_lines("chat_llm_latency_seconds_sum", "LLM 调用耗时总和", "summary",
                             _llm_latency_sum, seconds=True)
        out += _metric_lines("chat_llm_latency_seconds_count", "LLM 调用样本数", "summary", _llm_latency_count)
        out += _metric_lines("chat_guard_events_total", "Guard 事件（blocked/rewrote/fallback/sampled）",
                             "counter", _guard)
        if _http_total:
            out.append("# TYPE chat_http_requests_total counter")
            out.append("# HELP chat_http_requests_total HTTP 请求数")
            for key in sorted(_http_total):
                method, status = key.split("|", 1)
                out.append(f"chat_http_requests_total{{method=\"{method}\",status=\"{status}\"}} {_http_total[key]}")
        if _http_dur_sum:
            out.append("# TYPE chat_http_request_duration_seconds_sum summary")
            for key in sorted(_http_dur_sum):
                method, status = key.split("|", 1)
                out.append(f"chat_http_request_duration_seconds_sum{{method=\"{method}\",status=\"{status}\"}} {_http_dur_sum[key]:.6f}")
            out.append("# TYPE chat_http_request_duration_seconds_count summary")
            for key in sorted(_http_count):
                method, status = key.split("|", 1)
                out.append(f"chat_http_request_duration_seconds_count{{method=\"{method}\",status=\"{status}\"}} {_http_count[key]}")
    return "\n".join(out) + "\n"
