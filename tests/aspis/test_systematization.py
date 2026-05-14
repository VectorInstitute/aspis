"""Test for systematization module."""

import json
from unittest.mock import Mock, patch

from inspect_ai.dataset import Sample

from aspis.inferencer import ModelInfo
from aspis.systematization import (
    SYSTEMATIZATION_PAPER_PATH,
    SYSTEMATIZATION_PROMPT,
    SYSTEMATIZED_CONCEPTS_PROMPT,
    SystematizedConcept,
    get_systematization_questions,
    get_systematization_questions_prompt,
    get_systematized_concepts,
    get_systematized_concepts_prompt,
)


@patch("aspis.systematization.execute_samples_against_model")
def test_get_systematization_questions_success(mock_execute_samples: Mock) -> None:
    model_responses = [
        '["test question 1", "test question 2"]',
        '```json ["test question 1", "test question 2"]   ```  ',
    ]

    for model_response in model_responses:
        mock_execute_samples.return_value = [model_response]

        test_product_description = "test product description"
        test_risk_description = "test risk description"
        test_openai_api_key = "test api key"
        test_model_info = ModelInfo.OPENAI_GPT_4O

        questions = get_systematization_questions(
            product_description=test_product_description,
            risk_description=test_risk_description,
            api_key=test_openai_api_key,
            model_info=test_model_info,
        )

        assert questions == ["test question 1", "test question 2"]

        mock_execute_samples.assert_called_once_with(
            [
                Sample(
                    input=get_systematization_questions_prompt(test_product_description, test_risk_description),
                    target="",
                )
            ],
            test_model_info,
            test_openai_api_key,
        )

        mock_execute_samples.reset_mock()


@patch("aspis.systematization.execute_samples_against_model")
def test_get_systematization_questions_failure_invalid_results(mock_execute_samples: Mock) -> None:
    invalid_model_responses = [
        "invalid json",
        '[{"invalid": "json"}]',
        '{"invalid": "json"}',
        '[{"title": "test concept 1", "body": "test body 1"}]',
        '[{"body": "test body 2", "prompt_template": "test prompt template 2"}]',
        '[{"title": "test concept 3", "prompt_template": "test prompt template 3"]',
    ]

    for invalid_model_response in invalid_model_responses:
        mock_execute_samples.return_value = [invalid_model_response]

        test_product_description = "test product description"
        test_risk_description = "test risk description"
        test_openai_api_key = "test api key"
        test_model_info = ModelInfo.OPENAI_GPT_4O

        questions = get_systematization_questions(
            product_description=test_product_description,
            risk_description=test_risk_description,
            api_key=test_openai_api_key,
            model_info=test_model_info,
        )

        assert questions is None
        mock_execute_samples.assert_called_once_with(
            [
                Sample(
                    input=get_systematization_questions_prompt(test_product_description, test_risk_description),
                    target="",
                )
            ],
            test_model_info,
            test_openai_api_key,
        )
        mock_execute_samples.reset_mock()


@patch("aspis.systematization.execute_samples_against_model")
def test_get_systematized_concepts_success(mock_execute_samples: Mock) -> None:
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
        mock_execute_samples.return_value = [model_response]

        test_product_description = "test product description"
        test_risk_description = "test risk description"
        test_questions = ["test question 1", "test question 2"]
        test_answers = ["test answer to question 1", "test answer to question 2"]
        test_openai_api_key = "test api key"
        test_model_info = ModelInfo.OPENAI_GPT_4O

        systematized_concepts = get_systematized_concepts(
            product_description=test_product_description,
            risk_description=test_risk_description,
            questions=test_questions,
            answers=test_answers,
            api_key=test_openai_api_key,
            model_info=test_model_info,
        )

        mock_execute_samples.assert_called_once_with(
            [
                Sample(
                    input=get_systematized_concepts_prompt(
                        test_product_description,
                        test_risk_description,
                        test_questions,
                        test_answers,
                    ),
                    target="",
                )
            ],
            test_model_info,
            test_openai_api_key,
        )
        assert systematized_concepts == [SystematizedConcept(**test_concept) for test_concept in test_concepts]

        mock_execute_samples.reset_mock()


@patch("aspis.systematization.execute_samples_against_model")
def test_get_systematized_concepts_failure_invalid_results(mock_execute_samples: Mock) -> None:
    invalid_model_responses = [
        "invalid json",
        '["invalid", "json"]',
        '{"invalid": "json"}',
        '[{"title": "test concept 1", "body": "test body 1"}]',
        '[{"body": "test body 2", "prompt_template": "test prompt template 2"}]',
        '[{"title": "test concept 3", "prompt_template": "test prompt template 3"]',
    ]

    for invalid_model_response in invalid_model_responses:
        mock_execute_samples.return_value = [invalid_model_response]

        test_product_description = "test product description"
        test_risk_description = "test risk description"
        test_questions = ["test question 1", "test question 2"]
        test_answers = ["test answer to question 1", "test answer to question 2"]
        test_openai_api_key = "test api key"
        test_model_info = ModelInfo.OPENAI_GPT_4O

        systematized_concepts = get_systematized_concepts(
            product_description=test_product_description,
            risk_description=test_risk_description,
            questions=test_questions,
            answers=test_answers,
            api_key=test_openai_api_key,
            model_info=test_model_info,
        )

        assert systematized_concepts is None
        mock_execute_samples.assert_called_once_with(
            [
                Sample(
                    input=get_systematized_concepts_prompt(
                        test_product_description,
                        test_risk_description,
                        test_questions,
                        test_answers,
                    ),
                    target="",
                )
            ],
            test_model_info,
            test_openai_api_key,
        )
        mock_execute_samples.reset_mock()


def test_get_systematization_questions_prompt() -> None:
    test_product_description = "test product description"
    test_risk_description = "test risk description"

    prompt = get_systematization_questions_prompt(test_product_description, test_risk_description)

    expected_prompt = SYSTEMATIZATION_PROMPT.format(
        product_description=test_product_description,
        risk_description=test_risk_description,
        systematization_paper=SYSTEMATIZATION_PAPER_PATH.read_text(),
    )
    assert prompt == expected_prompt


def test_get_systematized_concepts_prompt() -> None:
    test_product_description = "test product description"
    test_risk_description = "test risk description"
    test_questions = ["test question 1", "test question 2"]
    test_answers = ["test answer to question 1", "test answer to question 2"]

    prompt = get_systematized_concepts_prompt(
        test_product_description, test_risk_description, test_questions, test_answers
    )

    questions_and_answers = "\n".join(
        [f"Q: {question}\nA: {answer}" for question, answer in zip(test_questions, test_answers, strict=True)]
    )
    expected_prompt = SYSTEMATIZED_CONCEPTS_PROMPT.format(
        product_description=test_product_description,
        risk_description=test_risk_description,
        systematization_paper=SYSTEMATIZATION_PAPER_PATH.read_text(),
        questions_and_answers=questions_and_answers,
    )
    assert prompt == expected_prompt
