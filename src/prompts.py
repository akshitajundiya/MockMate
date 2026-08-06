"""Loads agent prompts from the prompts/ directory.

Prompts use $placeholder syntax (string.Template) so literal JSON braces in the
prompt text never collide with substitution.
"""

from functools import lru_cache
from string import Template

from .config import PROMPTS_DIR


@lru_cache(maxsize=None)
def _raw(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def load(name: str, **variables: str) -> str:
    """Load a prompt by filename (without .md) and substitute $variables."""
    if not variables:
        return _raw(name)
    return Template(_raw(name)).safe_substitute(**variables)
