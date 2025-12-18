"""Test for model module."""

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from aspis.model import MODEL, TEMPERATURE, get_llm


def test_get_llm() -> None:
    test_openai_api_key = "test api key"

    llm = get_llm(test_openai_api_key)

    assert isinstance(llm, ChatOpenAI)
    assert llm.openai_api_key == SecretStr(test_openai_api_key)
    assert llm.model_name == MODEL
    assert llm.temperature == TEMPERATURE
