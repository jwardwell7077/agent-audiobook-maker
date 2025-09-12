"""LLM utilities for the audiobook maker."""

from .manager import LLMBackend, LLMService
from .client import OpenAICompatClient

__all__ = ["LLMBackend", "LLMService", "OpenAICompatClient"]

