"""
ChatState - LangGraph 状态定义
"""
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import MessagesState


class ChatState(MessagesState):
    """主聊天状态"""
    conversation_id: int
    user_id: int
    user_message: str
    user_message_type: str
    intent: str
    intent_confidence: float
    intent_signals: List[str]
    profile: Dict[str, Any]
    strategy: Dict[str, Any]
    ai_persona: Dict[str, Any]
    ai_response: str
    ai_response_type: str
    ai_media_url: str
    tool_calls: List[Dict[str, Any]]
    safety_passed: bool
    safety_issues: List[str]
    rewrite_count: int
    done: bool
    history: List[Dict[str, Any]]


def empty_profile() -> Dict[str, Any]:
    return {
        "identity_hints": [],
        "occupation_hints": [],
        "intent_signals": [],
        "scam_patterns": [],
        "relationship_stage": "initial",
        "trust_level": 50,
        "emotional_state": "neutral",
        "confidence": 0.0,
        "summary": "",
    }


def empty_persona() -> Dict[str, Any]:
    return {
        "name": "",
        "age": 0,
        "gender": "",
        "occupation": "",
        "background": "",
        "speaking_style": "",
        "knowledge_boundary": [],
        "emotional_traits": [],
        "current_goal": "",
    }
