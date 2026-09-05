"""
LLM Provider（方案 C：单次生成）
- RemoteLLM：DeepSeek / OpenAI 兼容 chat/completions
- MockLLM：离线确定性假回复（LLM_MODE=mock 或未配置有效 key），供开发与测试验收
- build_llm()：按配置选择，engine 只依赖 generate(system, user) -> str
"""
import hashlib

import httpx
from config import settings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class BaseLLM:
    async def generate(self, system: str, user: str) -> str:
        raise NotImplementedError


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
        return self._lines[idx]


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
        return await self._post(payload)


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
