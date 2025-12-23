"""Test for the API main module."""

from io import BytesIO
from unittest.mock import Mock, call, patch

import pytest
import yaml
from fastapi.testclient import TestClient

from aspis.api.main import app


@pytest.mark.integration_test
@patch("aspis.inferencer.get_llm")
def test_evaluate_from_file_success(mock_get_llm: Mock) -> None:
    test_scores = ["test score 1", "test score 2"]
    invoke_mock = Mock()
    invoke_mock.side_effect = [Mock(content=test_score) for test_score in test_scores]
    mock_get_llm.return_value = Mock(invoke=invoke_mock)

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

        assert mock_get_llm.call_count == 2
        assert invoke_mock.call_count == 2
        mock_get_llm.assert_has_calls(
            [
                call(test_openai_api_key),
                call().invoke(expected_prompts[0]),
                call(test_openai_api_key),
                call().invoke(expected_prompts[1]),
            ]
        )


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
