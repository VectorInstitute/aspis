"""Test for the API main module."""

from io import BytesIO
from unittest.mock import ANY, Mock, patch

import pytest
import yaml
from fastapi.testclient import TestClient
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate

from aspis.api.main import app
from aspis.inferencer import INFERENCE_MODEL


@pytest.mark.integration_test
@patch("aspis.inferencer.inspect_ai_eval")
def test_evaluate_from_file_success(mock_inspect_ai_eval: Mock) -> None:
    test_scores = ["test score 1", "test score 2"]
    invoke_mock = Mock()
    invoke_mock.side_effect = [Mock(content=test_score) for test_score in test_scores]
    mock_inspect_ai_eval.return_value = [
        Mock(
            samples=[
                Mock(output=Mock(choices=[Mock(message=Mock(content=test_scores[0]))])),
                Mock(output=Mock(choices=[Mock(message=Mock(content=test_scores[1]))])),
            ]
        ),
    ]

    """Test the API main module."""
    with TestClient(app) as client:
        test_text_to_evaluate = "Test text"
        test_openai_api_key = "test api key"
        test_systematized_concepts = [
            {
                "title": "Test concept 1",
                "prompt_template": "Test template 1 <text_to_evaluate/> text",
            },
            {
                "title": "Test concept 2",
                "prompt_template": "<text_to_evaluate/> Test template 2",
            },
        ]
        expected_prompts = [
            sys_concept["prompt_template"].replace("<text_to_evaluate/>", f"<text>{test_text_to_evaluate}</text>")
            for sys_concept in test_systematized_concepts
        ]

        file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": test_text_to_evaluate,
                "openai_api_key": test_openai_api_key,
            },
            files={
                "systematized_concepts_file": (
                    "systematized_concepts.yaml",
                    BytesIO(file_content),
                    "application/yaml",
                )
            },
        )

        assert response.status_code == 200
        json_response = response.json()
        for i in range(len(json_response)):
            assert json_response[i]["systematized_concept_title"] == test_systematized_concepts[i]["title"]
            assert json_response[i]["result"] == test_scores[i]
            assert json_response[i]["prompt"] == expected_prompts[i]

        mock_inspect_ai_eval.assert_called_once_with(ANY, model=INFERENCE_MODEL, log_dir=ANY)

        inspect_call_args = mock_inspect_ai_eval.call_args_list[0][0][0]
        assert expected_prompts == [s.input for s in inspect_call_args.dataset.samples]
        assert len(inspect_call_args.solver) == 1
        assert inspect_call_args.solver[0].__qualname__ == generate().__qualname__
        assert len(inspect_call_args.scorer) == 1
        assert inspect_call_args.scorer[0].__qualname__ == model_graded_qa().__qualname__


@pytest.mark.integration_test
def test_evaluate_from_file_failure_bad_format() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "openai_api_key": "test api key",
            },
            files={
                "systematized_concepts_file": (
                    "systematized_concepts.yaml",
                    BytesIO(b"[invalid yaml"),
                    "application/yaml",
                )
            },
        )
        assert response.status_code == 500
        assert "Evaluation failed: while parsing a flow sequence" in response.json()["detail"]


@pytest.mark.integration_test
def test_evaluate_from_file_failure_missing_fields() -> None:
    files_contents = [
        {"something else": "test"},
        {"systematized_concepts": [{"title": "Test concept 1"}]},
        {"systematized_concepts": [{"prompt_template": "Test prompt template 2"}]},
    ]
    for file_contents in files_contents:
        with TestClient(app) as client:
            response = client.post(
                "/evaluate_from_file",
                data={
                    "text_to_evaluate": "Test text",
                    "openai_api_key": "test api key",
                },
                files={
                    "systematized_concepts_file": (
                        "systematized_concepts.yaml",
                        BytesIO(yaml.safe_dump(file_contents).encode("utf-8")),
                        "application/yaml",
                    )
                },
            )
            assert response.status_code == 422
            assert (
                "The file must contain" in response.json()["detail"]
                or "Systematized concepts must contain" in response.json()["detail"]
            )


@pytest.mark.integration_test
@patch("aspis.inferencer.inspect_ai_eval")
def test_evaluate_from_file_failure_assertions(mock_inspect_ai_eval: Mock) -> None:
    return_values_and_error_messages = [
        ([], "Expected exactly one result"),
        (["a", "b"], "Expected exactly one result"),
        ([Mock(samples=None)], "Expected samples to be not None"),
        ([Mock(samples=[])], "Expected number of samples to be the same as the number of samples in the task"),
        ([Mock(samples=["a", "b"])], "Expected number of samples to be the same as the number of samples in the task"),
        (
            [Mock(samples=[Mock(output=Mock(choices=[Mock(message=Mock(content=123))]))])],
            "Expected message content to be a string",
        ),
    ]

    for return_value, error_message in return_values_and_error_messages:
        mock_inspect_ai_eval.return_value = return_value

        """Test the API main module."""
        with TestClient(app) as client:
            file_content = yaml.safe_dump(
                {
                    "systematized_concepts": [
                        {
                            "title": "Test concept 1",
                            "prompt_template": "Test template 1 <text_to_evaluate/> text",
                        },
                    ]
                }
            ).encode("utf-8")

            response = client.post(
                "/evaluate_from_file",
                data={
                    "text_to_evaluate": "Test text",
                    "openai_api_key": "test api key",
                },
                files={
                    "systematized_concepts_file": (
                        "systematized_concepts.yaml",
                        BytesIO(file_content),
                        "application/yaml",
                    )
                },
            )

            assert response.status_code == 422
            assert response.json()["detail"] == error_message

        mock_inspect_ai_eval.reset_mock()
