"""M5.5（R-A2）：LLM 上游熔断 + 并发预算护栏。

- 连续失败达阈值 → 熔断打开：窗口内不再发起网络（引擎侧自动走降级话术）；
- 冷却结束 → 半开探活：成功即关闭，失败重新打开；
- 全局并发超限 → 直接抛预算异常（不排队，避免请求堆积压垮上游）。
"""
import asyncio

import httpx
import pytest
from config import settings
from core import metrics
from llm.provider import (
    LLMBudgetExceededError,
    LLMCircuitOpenError,
    MockLLM,
    RemoteLLM,
    reset_llm_guards,
)


def _remote(monkeypatch, *, threshold=2, cooldown=0.05, concurrency=4) -> RemoteLLM:
    monkeypatch.setattr(settings, "LLM_CIRCUIT_FAIL_THRESHOLD", threshold)
    monkeypatch.setattr(settings, "LLM_CIRCUIT_COOLDOWN_S", cooldown)
    monkeypatch.setattr(settings, "LLM_MAX_CONCURRENCY", concurrency)
    reset_llm_guards()
    return RemoteLLM(api_key="sk-test", base_url="http://unused.local", model="m")


def _fail_post(network_calls: list):
    async def fake_post(payload: dict) -> str:
        network_calls.append(payload)
        raise httpx.TransportError("upstream down")
    return fake_post


async def test_circuit_opens_and_rejects_without_network(monkeypatch):
    metrics.reset()
    calls: list = []
    llm = _remote(monkeypatch, threshold=2)
    llm._post = _fail_post(calls)  # noqa: SLF001 - 测试注入假上游
    with pytest.raises(httpx.TransportError):
        await llm.generate("s", "u")
    with pytest.raises(httpx.TransportError):
        await llm.generate("s", "u")  # 第 2 次失败触发熔断
    n_before = len(calls)
    with pytest.raises(LLMCircuitOpenError):
        await llm.generate("s", "u")
    assert len(calls) == n_before  # 熔断窗口内不再打网络
    out = metrics.render()
    assert 'chat_llm_circuit_total{kind="opened"} 1' in out
    assert 'chat_llm_circuit_total{kind="rejected"} 1' in out


async def test_circuit_half_open_probe_success_closes(monkeypatch):
    metrics.reset()
    llm = _remote(monkeypatch, threshold=1, cooldown=0.05)
    calls: list = []
    llm._post = _fail_post(calls)
    with pytest.raises(httpx.TransportError):
        await llm.generate("s", "u")  # 1 次失败即熔断
    assert 'chat_llm_circuit_total{kind="opened"} 1' in metrics.render()

    await asyncio.sleep(0.06)  # 冷却结束 → 半开

    async def ok_post(payload: dict) -> str:
        return "hi"

    llm._post = ok_post
    assert await llm.generate("s", "u") == "hi"  # 探活成功
    out = metrics.render()
    assert 'chat_llm_circuit_total{kind="closed"} 1' in out
    assert await llm.generate("s", "u") == "hi"  # 已关闭，继续正常


async def test_circuit_half_open_probe_failure_reopens(monkeypatch):
    metrics.reset()
    llm = _remote(monkeypatch, threshold=1, cooldown=0.05)
    calls: list = []
    llm._post = _fail_post(calls)
    with pytest.raises(httpx.TransportError):
        await llm.generate("s", "u")  # 熔断
    await asyncio.sleep(0.06)  # 半开
    with pytest.raises(httpx.TransportError):
        await llm.generate("s", "u")  # 探活失败 → 重新熔断
    with pytest.raises(LLMCircuitOpenError):
        await llm.generate("s", "u")
    assert 'chat_llm_circuit_total{kind="opened"} 2' in metrics.render()


async def test_budget_rejects_over_concurrency(monkeypatch):
    metrics.reset()
    llm = _remote(monkeypatch, concurrency=1, threshold=99)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_post(payload: dict) -> str:
        started.set()
        await release.wait()
        return "slow-ok"

    llm._post = slow_post
    first = asyncio.create_task(llm.generate("s", "u"))
    await started.wait()  # 占满唯一额度
    with pytest.raises(LLMBudgetExceededError):
        await llm.generate("s", "u")
    assert 'chat_llm_circuit_total{kind="rejected"} 1' in metrics.render()
    release.set()
    assert await first == "slow-ok"
    assert await llm.generate("s", "u") == "slow-ok"  # 释放后恢复


async def test_extract_json_none_while_open_without_network(monkeypatch):
    metrics.reset()
    llm = _remote(monkeypatch, threshold=1, cooldown=5.0)
    calls: list = []
    llm._post = _fail_post(calls)
    with pytest.raises(httpx.TransportError):
        await llm.generate("s", "u")  # 熔断（冷却 5s，测试内不会过期）
    n_before = len(calls)
    assert await llm.extract_json("s", "u") is None
    assert len(calls) == n_before
    assert 'chat_llm_circuit_total{kind="rejected"} 1' in metrics.render()


async def test_mock_llm_never_tripped_by_breaker(monkeypatch):
    reset_llm_guards()
    monkeypatch.setattr(settings, "LLM_CIRCUIT_FAIL_THRESHOLD", 1)
    llm = MockLLM()
    text = await llm.generate("s", "u")
    assert text  # mock 模式始终离线可用，不受熔断影响
