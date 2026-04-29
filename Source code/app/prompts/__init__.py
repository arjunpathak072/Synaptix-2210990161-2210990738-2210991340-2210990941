"""Prompt loader — reads .md files from the prompts directory."""

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


@lru_cache
def load(name: str) -> str:
    """Load a prompt template by name (without extension)."""
    return (_PROMPTS_DIR / f"{name}.md").read_text()
