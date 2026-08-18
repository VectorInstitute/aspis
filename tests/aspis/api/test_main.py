"""Test for the API main module."""

import json
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

from aspis.api.main import app
from aspis.inferencer import DEFAULT_OPENAI_TIMEOUT_SECONDS
from aspis.providers import ModelInfo
from aspis.utils import clean_model_output


def _mock_completion(content: str) -> Mock:
    return Mock(choices=[Mock(message=Mock(content=content))])


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_evaluate_from_file_success(mock_openai: Mock) -> None:
    test_scores = ['{"score": "test score 1"}', '```json{"score": "test score 2"}```', "not a valid json test score"]
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = [_mock_completion(score) for score in test_scores]

    with TestClient(app) as client:
        test_text_to_evaluate = "Test text"
        test_api_key = "test api key"
        test_systematized_concepts = [
            {
                "title": "Test concept 1",
                "prompt_template": "Test template 1 <text_to_evaluate/> text",
            },
            {
                "title": "Test concept 2",
                "prompt_template": "<text_to_evaluate/> Test template 2",
            },
            {
                "title": "Test concept 3",
                "prompt_template": "<text_to_evaluate/> Test template 3",
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
                "api_key": test_api_key,
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
            # Parsing all the scores but the last one, which is not a valid json.
            if i != len(test_scores) - 1:
                expected_result = json.loads(clean_model_output(test_scores[i]))
            else:
                expected_result = {"raw_output": test_scores[i]}

            assert json_response[i]["systematized_concept_title"] == test_systematized_concepts[i]["title"]
            assert json_response[i]["result"] == expected_result
            assert json_response[i]["prompt"] == expected_prompts[i]

        mock_openai.assert_called_once_with(
            api_key=test_api_key,
            base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
            timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
        )
        assert mock_client.chat.completions.create.call_count == len(test_systematized_concepts)
        for expected_prompt in expected_prompts:
            mock_client.chat.completions.create.assert_any_call(
                model=ModelInfo.OPENAI_GPT_4O.model_id,
                messages=[{"role": "user", "content": expected_prompt}],
            )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_evaluate_from_file_failure_evaluation_error(mock_openai: Mock) -> None:
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = RuntimeError("Test error")

    with TestClient(app) as client:
        test_systematized_concepts = [
            {"title": "Test concept 1", "prompt_template": "Test template 1 <text_to_evaluate/> text"}
        ]

        file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": "test api key",
            },
            files={
                "systematized_concepts_file": (
                    "systematized_concepts.yaml",
                    BytesIO(file_content),
                    "application/yaml",
                )
            },
        )
        assert response.status_code == 500
        json_response = response.json()

        assert json_response == {"detail": "Evaluation failed: Error during evaluation."}


@pytest.mark.integration_test
def test_evaluate_from_file_failure_bad_format() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": "test api key",
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
@patch("aspis.inferencer.OpenAI")
def test_evaluate_from_file_with_model_success(mock_openai: Mock) -> None:
    test_systematized_concepts = [
        {"title": "Test concept 1", "prompt_template": "Test template 1 <text_to_evaluate/> text"}
    ]
    file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = _mock_completion('{"score": "test score 1"}')

    test_model_id = ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW.model_id
    test_api_key = "test api key"

    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": test_api_key,
                "model": test_model_id,
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
        mock_openai.assert_called_once_with(
            api_key=test_api_key,
            base_url=ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW.provider_url,
            timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
        )
        mock_client.chat.completions.create.assert_called_once_with(
            model=test_model_id,
            messages=[
                {
                    "role": "user",
                    "content": "Test template 1 <text>Test text</text> text",
                }
            ],
        )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_evaluate_from_file_strips_whitespace_padded_known_model(mock_openai: Mock) -> None:
    test_systematized_concepts = [
        {"title": "Test concept 1", "prompt_template": "Test template 1 <text_to_evaluate/> text"}
    ]
    file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = _mock_completion('{"score": "ok"}')

    test_api_key = "test api key"

    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": test_api_key,
                "model": f"  {ModelInfo.OPENAI_GPT_4O.model_id}  ",
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
        mock_openai.assert_called_once_with(
            api_key=test_api_key,
            base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
            timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
        )
        mock_client.chat.completions.create.assert_called_once_with(
            model=ModelInfo.OPENAI_GPT_4O.model_id,
            messages=[
                {
                    "role": "user",
                    "content": "Test template 1 <text>Test text</text> text",
                }
            ],
        )


@pytest.mark.integration_test
def test_evaluate_from_file_custom_model_requires_proxy() -> None:
    test_systematized_concepts = [
        {"title": "Test concept 1", "prompt_template": "Test template 1 <text_to_evaluate/> text"}
    ]
    file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")

    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": "test api key",
                "model": "my-custom-model",
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
        assert "Please enter a proxy address for custom model IDs" in response.json()["detail"]


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_evaluate_from_file_custom_model_with_proxy_success(mock_openai: Mock) -> None:
    test_systematized_concepts = [
        {"title": "Test concept 1", "prompt_template": "Test template 1 <text_to_evaluate/> text"}
    ]
    file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")
    test_proxy = "https://1.1.1.1/v1"
    test_api_key = "test api key"
    test_model = "my-custom-model"

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = _mock_completion('{"score": "ok"}')

    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": test_api_key,
                "model": test_model,
                "proxy_base_url": test_proxy,
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
        mock_openai.assert_called_once_with(
            api_key=test_api_key, base_url=test_proxy, timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS
        )
        mock_client.chat.completions.create.assert_called_once_with(
            model=test_model,
            messages=[
                {
                    "role": "user",
                    "content": "Test template 1 <text>Test text</text> text",
                }
            ],
        )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_evaluate_from_file_known_model_with_proxy_override(mock_openai: Mock) -> None:
    test_systematized_concepts = [
        {"title": "Test concept 1", "prompt_template": "Test template 1 <text_to_evaluate/> text"}
    ]
    file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")
    test_proxy = "https://1.1.1.1/v1"
    test_api_key = "test api key"

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = _mock_completion('{"score": "ok"}')

    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": test_api_key,
                "model": ModelInfo.OPENAI_GPT_4O.model_id,
                "proxy_base_url": test_proxy,
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
        mock_openai.assert_called_once_with(
            api_key=test_api_key, base_url=test_proxy, timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS
        )


@pytest.mark.integration_test
def test_evaluate_from_file_invalid_proxy_url() -> None:
    test_systematized_concepts = [
        {"title": "Test concept 1", "prompt_template": "Test template 1 <text_to_evaluate/> text"}
    ]
    file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")

    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": "test api key",
                "model": ModelInfo.OPENAI_GPT_4O.model_id,
                "proxy_base_url": "not-a-valid-url",
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
        assert "Please enter a valid proxy address URL" in response.json()["detail"]


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_evaluate_from_file_empty_proxy_skips_validation(mock_openai: Mock) -> None:
    test_systematized_concepts = [
        {"title": "Test concept 1", "prompt_template": "Test template 1 <text_to_evaluate/> text"}
    ]
    file_content = yaml.safe_dump({"systematized_concepts": test_systematized_concepts}).encode("utf-8")
    test_api_key = "test api key"

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = _mock_completion('{"score": "ok"}')

    with TestClient(app) as client:
        response = client.post(
            "/evaluate_from_file",
            data={
                "text_to_evaluate": "Test text",
                "api_key": test_api_key,
                "model": ModelInfo.OPENAI_GPT_4O.model_id,
                "proxy_base_url": "   ",
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
        mock_openai.assert_called_once_with(
            api_key=test_api_key,
            base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
            timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
        )


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
                    "api_key": "test api key",
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
@patch("aspis.inferencer.OpenAI")
def test_evaluate_from_file_failure_assertions(mock_openai: Mock) -> None:
    return_values_and_expectations = [
        (
            Mock(choices=[]),
            422,
            "Expected at least one choice in the model response",
        ),
        (
            Mock(choices=[Mock(message=Mock(content=123))]),
            422,
            "Unsupported model output content type: <class 'int'>",
        ),
    ]

    for return_value, expected_status, error_message in return_values_and_expectations:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.chat.completions.create.return_value = return_value

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
                    "api_key": "test api key",
                },
                files={
                    "systematized_concepts_file": (
                        "systematized_concepts.yaml",
                        BytesIO(file_content),
                        "application/yaml",
                    )
                },
            )

            assert response.status_code == expected_status
            assert response.json()["detail"] == error_message

        mock_openai.reset_mock()
