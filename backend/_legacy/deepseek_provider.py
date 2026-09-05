"""
LLM 适配层 - DeepSeek (OpenAI 兼容)
"""
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from config import settings


class DeepSeekLLM:
    """DeepSeek 适配 - 通过 langchain-openai 的 OpenAI 兼容模式"""

    def __init__(
        self,
        temperature: float = 0.8,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        timeout: int = 60,
    ):
        self.llm = ChatOpenAI(
            model=model or settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def invoke(self, messages: List[BaseMessage]):
        return self.llm.invoke(messages)

    async def ainvoke(self, messages: List[BaseMessage]):
        return await self.llm.ainvoke(messages)

    def bind_tools(self, tools: List[Any]):
        return self.llm.bind_tools(tools)


# === 不同 Agent 用的不同温度 ===
def make_router_llm() -> DeepSeekLLM:
    """Router 意图分类 - 低温度，确定性"""
    return DeepSeekLLM(temperature=0.1, max_tokens=256)


def make_profile_llm() -> DeepSeekLLM:
    """Profile 画像识别 - 低温度"""
    return DeepSeekLLM(temperature=0.3, max_tokens=512)


def make_strategy_llm() -> DeepSeekLLM:
    """Strategy 策略生成 - 中温度"""
    return DeepSeekLLM(temperature=0.6, max_tokens=512)


def make_actor_llm() -> DeepSeekLLM:
    """Actor 角色演绎 - 高温度，更随机、更像人"""
    return DeepSeekLLM(temperature=0.95, max_tokens=512)


def make_safety_llm() -> DeepSeekLLM:
    """Safety 检测 - 低温度"""
    return DeepSeekLLM(temperature=0.2, max_tokens=256)


def make_reflector_llm() -> DeepSeekLLM:
    """Reflector 复盘 - 中温度"""
    return DeepSeekLLM(temperature=0.4, max_tokens=512)
