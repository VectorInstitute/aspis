"""Test for sistematization module."""

from unittest.mock import Mock, patch

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from aspis.sistematization import (
    MODEL,
    SISTEMATIZATION_PAPER_PATH,
    SISTEMATIZATION_PROMPT,
    TEMPERATURE,
    get_llm,
    get_sistematization_questions,
)


@patch("aspis.sistematization.get_llm")
def test_get_sistematization_questions_success(mock_get_llm: Mock) -> None:
    invoke_mock = Mock()
    invoke_mock.return_value = Mock(content='["test question 1", "test question 2"]')
    mock_get_llm.return_value = Mock(invoke=invoke_mock)

    test_product_description = "test product description"
    test_risk_description = "test risk description"
    test_openai_api_key = "test api key"

    questions = get_sistematization_questions(
        product_description=test_product_description,
        risk_description=test_risk_description,
        openai_api_key=test_openai_api_key,
    )

    assert questions == ["test question 1", "test question 2"]

    assert mock_get_llm.has_been_called_once_with(test_openai_api_key)
    assert invoke_mock.has_been_called_once_with(
        SISTEMATIZATION_PROMPT.format(
            product_description=test_product_description,
            risk_description=test_risk_description,
            sistematization_paper=SISTEMATIZATION_PAPER_PATH.read_text(),
        )
    )


@patch("aspis.sistematization.get_llm")
def test_get_sistematization_questions_failure(mock_get_llm: Mock) -> None:
    invoke_mock = Mock()
    invoke_mock.return_value = Mock(content="invalid json")
    mock_get_llm.return_value = Mock(invoke=invoke_mock)

    test_product_description = "test product description"
    test_risk_description = "test risk description"
    test_openai_api_key = "test api key"

    questions = get_sistematization_questions(
        product_description=test_product_description,
        risk_description=test_risk_description,
        openai_api_key=test_openai_api_key,
    )

    assert questions is None
    assert mock_get_llm.has_been_called_once_with(test_openai_api_key)
    assert invoke_mock.has_been_called_once_with(
        SISTEMATIZATION_PROMPT.format(
            product_description=test_product_description,
            risk_description=test_risk_description,
            sistematization_paper=SISTEMATIZATION_PAPER_PATH.read_text(),
        )
    )


def test_get_llm() -> None:
    test_openai_api_key = "test api key"

    llm = get_llm(test_openai_api_key)

    assert isinstance(llm, ChatOpenAI)
    assert llm.openai_api_key == SecretStr(test_openai_api_key)
    assert llm.model_name == MODEL
    assert llm.temperature == TEMPERATURE
