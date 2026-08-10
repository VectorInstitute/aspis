"""Tests for the inferencer module."""

import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from aspis.inferencer import (
    DEFAULT_PROXY_BASE_URL,
    ModelInfo,
    Sample,
    create_openai_client,
    execute_samples_against_model,
    extract_string_output,
)


def test_extract_string_output() -> None:
    test_cases = [
        ("test score", "test score"),
        (["part1", "part2"], "part2"),
        ([Mock(text="test score")], "test score"),
        ([{"text": "test score"}], "test score"),
        # Reasoning then answer: take the final non-reasoning text part.
        ([SimpleNamespace(text="reasoning"), SimpleNamespace(text="answer")], "answer"),
        (
            [
                SimpleNamespace(type="reasoning", text="thinking..."),
                SimpleNamespace(type="text", text='{"score": 1}'),
            ],
            '{"score": 1}',
        ),
        (
            [
                {"type": "thinking", "text": "step by step"},
                {"type": "text", "text": "final answer"},
            ],
            "final answer",
        ),
    ]

    for model_output, expected_output in test_cases:
        assert extract_string_output(model_output) == expected_output


def test_extract_string_output_unsupported() -> None:
    with pytest.raises(ValueError, match="Unsupported model output content type"):
        extract_string_output(123)


@patch("aspis.inferencer.OpenAI")
def test_create_openai_client_passes_api_key_and_proxy(mock_openai: Mock) -> None:
    api_key = "test-api-key"
    create_openai_client(api_key)

    mock_openai.assert_called_once_with(api_key=api_key, base_url=DEFAULT_PROXY_BASE_URL)
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("GOOGLE_API_KEY") is None
    assert os.environ.get("ANTHROPIC_API_KEY") is None


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_uses_per_call_client(mock_openai: Mock) -> None:
    api_key = "caller-api-key"
    model_info = ModelInfo.OPENAI_GPT_4O
    samples = [Sample(input="prompt one"), Sample(input="prompt two")]

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content="output one"))]),
        Mock(choices=[Mock(message=Mock(content="output two"))]),
    ]

    outputs = execute_samples_against_model(samples, model_info, api_key)

    assert outputs == ["output one", "output two"]
    mock_openai.assert_called_once_with(api_key=api_key, base_url=DEFAULT_PROXY_BASE_URL)
    assert mock_client.chat.completions.create.call_count == 2
    mock_client.chat.completions.create.assert_any_call(
        model=model_info.model_id,
        messages=[{"role": "user", "content": "prompt one"}],
    )
    mock_client.chat.completions.create.assert_any_call(
        model=model_info.model_id,
        messages=[{"role": "user", "content": "prompt two"}],
    )
    mock_client.__exit__.assert_called_once()
    assert os.environ.get(model_info.api_key_name) is None


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_raises_on_api_error(mock_openai: Mock) -> None:
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = RuntimeError("boom")

    with pytest.raises(ValueError, match="Error during evaluation") as exc_info:
        execute_samples_against_model([Sample(input="prompt")], ModelInfo.OPENAI_GPT_4O, "key")

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    mock_openai.assert_called_once_with(api_key="key", base_url=DEFAULT_PROXY_BASE_URL)
    mock_client.__exit__.assert_called_once()


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_raises_on_empty_choices(mock_openai: Mock) -> None:
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = Mock(choices=[])

    with pytest.raises(ValueError, match="Expected at least one choice"):
        execute_samples_against_model([Sample(input="prompt")], ModelInfo.OPENAI_GPT_4O, "key")
