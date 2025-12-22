"""Definitions pertaining to models."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


MODEL = "gpt-4o"
TEMPERATURE = 0.7


def get_llm(api_key: str) -> BaseChatModel:
    """Get the LLM object.

    Args:
        api_key: The OpenAI API key to set up the LLM.

    Returns:
        The LLM.
    """
    return ChatOpenAI(model=MODEL, temperature=TEMPERATURE, api_key=SecretStr(api_key))
