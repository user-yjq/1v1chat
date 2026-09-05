"""Prompt 模板加载器：模板统一放本目录（backend/llm/prompts/）"""
from pathlib import Path

PROMPT_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")
