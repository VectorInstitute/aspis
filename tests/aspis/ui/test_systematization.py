"""Test for systematization module."""

import json
from unittest.mock import Mock, patch

from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from pytest import raises

from aspis.ui.systematization import (
    MODEL,
    SYSTEMATIZATION_PAPER_PATH,
    SYSTEMATIZATION_PROMPT,
    SYSTEMATIZED_CONCEPTS_PROMPT,
    TEMPERATURE,
    SystematizedConcept,
    format_questions_and_answers,
    get_llm,
    get_systematization_questions,
    get_systematized_concepts,
)


@patch("aspis.ui.systematization.get_llm")
def test_get_systematization_questions_success(mock_get_llm: Mock) -> None:
    model_responses = [
        '["test question 1", "test question 2"]',
        '```json ["test question 1", "test question 2"]   ```  ',
    ]

    for model_response in model_responses:
        invoke_mock = Mock()
        invoke_mock.return_value = Mock(content=model_response)
        mock_get_llm.return_value = Mock(invoke=invoke_mock)

        test_product_description = "test product description"
        test_risk_description = "test risk description"
        test_openai_api_key = "test api key"

        questions = get_systematization_questions(
            product_description=test_product_description,
            risk_description=test_risk_description,
            openai_api_key=test_openai_api_key,
        )

        assert questions == ["test question 1", "test question 2"]

        mock_get_llm.assert_called_once_with(test_openai_api_key)
        invoke_mock.assert_called_once_with(
            SYSTEMATIZATION_PROMPT.format(
                product_description=test_product_description,
                risk_description=test_risk_description,
                systematization_paper=SYSTEMATIZATION_PAPER_PATH.read_text(),
            )
        )

        mock_get_llm.reset_mock()


@patch("aspis.ui.systematization.get_llm")
def test_get_systematization_questions_failure_invalid_results(mock_get_llm: Mock) -> None:
    invalid_model_responses = [
        "invalid json",
        '[{"invalid": "json"}]',
        '{"invalid": "json"}',
        '[{"title": "test concept 1", "body": "test body 1"}]',
        '[{"body": "test body 2", "prompt_template": "test prompt template 2"}]',
        '[{"title": "test concept 3", "prompt_template": "test prompt template 3"]',
    ]

    for invalid_model_response in invalid_model_responses:
        invoke_mock = Mock()
        invoke_mock.return_value = Mock(content=invalid_model_response)
        mock_get_llm.return_value = Mock(invoke=invoke_mock)

        test_product_description = "test product description"
        test_risk_description = "test risk description"
        test_openai_api_key = "test api key"

        questions = get_systematization_questions(
            product_description=test_product_description,
            risk_description=test_risk_description,
            openai_api_key=test_openai_api_key,
        )

        assert questions is None
        mock_get_llm.assert_called_once_with(test_openai_api_key)
        invoke_mock.assert_called_once_with(
            SYSTEMATIZATION_PROMPT.format(
                product_description=test_product_description,
                risk_description=test_risk_description,
                systematization_paper=SYSTEMATIZATION_PAPER_PATH.read_text(),
            )
        )

        mock_get_llm.reset_mock()


@patch("aspis.ui.systematization.get_llm")
def test_get_systematized_concepts_success(mock_get_llm: Mock) -> None:
    test_concepts = [
        {
            "title": "test concept 1",
            "body": "test body 1",
            "prompt_template": "test prompt template 1",
        },
        {
            "title": "test concept 2",
            "body": "test body 2",
            "prompt_template": "test prompt template 2",
        },
    ]
    model_responses = [
        json.dumps(test_concepts),
        "```json " + json.dumps(test_concepts) + " ```",
    ]

    for model_response in model_responses:
        invoke_mock = Mock()
        invoke_mock.return_value = Mock(content=model_response)
        mock_get_llm.return_value = Mock(invoke=invoke_mock)

        test_product_description = "test product description"
        test_risk_description = "test risk description"
        test_questions = ["test question 1", "test question 2"]
        test_answers = ["test answer to question 1", "test answer to question 2"]
        test_openai_api_key = "test api key"

        systematized_concepts = get_systematized_concepts(
            product_description=test_product_description,
            risk_description=test_risk_description,
            questions=test_questions,
            answers=test_answers,
            openai_api_key=test_openai_api_key,
        )

        mock_get_llm.assert_called_once_with(test_openai_api_key)
        invoke_mock.assert_called_once_with(
            SYSTEMATIZED_CONCEPTS_PROMPT.format(
                product_description=test_product_description,
                risk_description=test_risk_description,
                systematization_paper=SYSTEMATIZATION_PAPER_PATH.read_text(),
                questions_and_answers=format_questions_and_answers(test_questions, test_answers),
            )
        )
        assert systematized_concepts == [SystematizedConcept(**test_concept) for test_concept in test_concepts]

        mock_get_llm.reset_mock()


@patch("aspis.ui.systematization.get_llm")
def test_get_systematized_concepts_failure_invalid_results(mock_get_llm: Mock) -> None:
    invalid_model_responses = [
        "invalid json",
        '["invalid", "json"]',
        '{"invalid": "json"}',
        '[{"title": "test concept 1", "body": "test body 1"}]',
        '[{"body": "test body 2", "prompt_template": "test prompt template 2"}]',
        '[{"title": "test concept 3", "prompt_template": "test prompt template 3"]',
    ]

    for invalid_model_response in invalid_model_responses:
        invoke_mock = Mock()
        invoke_mock.return_value = Mock(content=invalid_model_response)
        mock_get_llm.return_value = Mock(invoke=invoke_mock)

        test_product_description = "test product description"
        test_risk_description = "test risk description"
        test_questions = ["test question 1", "test question 2"]
        test_answers = ["test answer to question 1", "test answer to question 2"]
        test_openai_api_key = "test api key"

        systematized_concepts = get_systematized_concepts(
            product_description=test_product_description,
            risk_description=test_risk_description,
            questions=test_questions,
            answers=test_answers,
            openai_api_key=test_openai_api_key,
        )

        assert systematized_concepts is None
        mock_get_llm.assert_called_once_with(test_openai_api_key)
        invoke_mock.assert_called_once_with(
            SYSTEMATIZED_CONCEPTS_PROMPT.format(
                product_description=test_product_description,
                risk_description=test_risk_description,
                systematization_paper=SYSTEMATIZATION_PAPER_PATH.read_text(),
                questions_and_answers=format_questions_and_answers(test_questions, test_answers),
            )
        )

        mock_get_llm.reset_mock()


def test_format_questions_and_answers_success() -> None:
    test_questions = ["test question 1", "test question 2"]
    test_answers = ["test answer to question 1", "test answer to question 2"]

    result = format_questions_and_answers(test_questions, test_answers)

    assert result == "\n".join(
        [f"Q: {question}\nA: {answer}" for question, answer in zip(test_questions, test_answers)]
    )


def test_format_questions_and_answers_failure_mismatched_lengths() -> None:
    test_questions = ["test question 1", "test question 2"]
    test_answers = ["test answer to question 1"]

    with raises(ValueError):
        format_questions_and_answers(test_questions, test_answers)


def test_get_llm() -> None:
    test_openai_api_key = "test api key"

    llm = get_llm(test_openai_api_key)

    assert isinstance(llm, ChatOpenAI)
    assert llm.openai_api_key == SecretStr(test_openai_api_key)
    assert llm.model_name == MODEL
    assert llm.temperature == TEMPERATURE
