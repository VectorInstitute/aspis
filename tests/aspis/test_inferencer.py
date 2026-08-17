"""Tests for the inferencer module."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from aspis.inferencer import (
    DEFAULT_OPENAI_TIMEOUT_SECONDS,
    create_openai_client,
    evaluate_text,
    execute_samples_against_model,
    extract_string_output,
    get_inference_prompt,
)
from aspis.providers import ModelInfo


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
def test_create_openai_client_passes_api_key_and_provider_url(mock_openai: Mock) -> None:
    api_key = "test-api-key"
    model = ModelInfo.OPENAI_GPT_4O
    create_openai_client(api_key, model.provider_url)

    mock_openai.assert_called_once_with(
        api_key=api_key,
        base_url=model.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


@patch("aspis.inferencer.OpenAI")
def test_create_openai_client_with_custom_provider_url(mock_openai: Mock) -> None:
    provider_url = "https://1.1.1.1/v1"
    create_openai_client("key", provider_url)
    mock_openai.assert_called_once_with(
        api_key="key",
        base_url=provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_uses_per_call_client(mock_openai: Mock) -> None:
    api_key = "caller-api-key"
    model = ModelInfo.OPENAI_GPT_4O
    prompts = ["prompt one", "prompt two"]

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content="output one"))]),
        Mock(choices=[Mock(message=Mock(content="output two"))]),
    ]

    outputs = execute_samples_against_model(prompts, model.model_id, api_key, model.provider_url)

    assert outputs == ["output one", "output two"]
    mock_openai.assert_called_once_with(
        api_key=api_key,
        base_url=model.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
    assert mock_client.chat.completions.create.call_count == 2
    mock_client.chat.completions.create.assert_any_call(
        model=model.model_id,
        messages=[{"role": "user", "content": "prompt one"}],
    )
    mock_client.chat.completions.create.assert_any_call(
        model=model.model_id,
        messages=[{"role": "user", "content": "prompt two"}],
    )
    mock_client.__exit__.assert_called_once()


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_custom_model_and_proxy(mock_openai: Mock) -> None:
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = Mock(choices=[Mock(message=Mock(content="ok"))])
    provider_url = "https://1.1.1.1/v1"

    outputs = execute_samples_against_model(
        ["prompt"],
        "my-custom-model",
        "key",
        provider_url,
    )

    assert outputs == ["ok"]
    mock_openai.assert_called_once_with(
        api_key="key",
        base_url=provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
    mock_client.chat.completions.create.assert_called_once_with(
        model="my-custom-model",
        messages=[{"role": "user", "content": "prompt"}],
    )


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_raises_on_api_error(mock_openai: Mock) -> None:
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = RuntimeError("boom")
    model = ModelInfo.OPENAI_GPT_4O

    with pytest.raises(RuntimeError, match="Error during evaluation") as exc_info:
        execute_samples_against_model(["prompt"], model.model_id, "key", model.provider_url)

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    mock_openai.assert_called_once_with(
        api_key="key",
        base_url=model.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
    mock_client.__exit__.assert_called_once()


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_raises_on_empty_choices(mock_openai: Mock) -> None:
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = Mock(choices=[])
    model = ModelInfo.OPENAI_GPT_4O

    with pytest.raises(ValueError, match="Expected at least one choice"):
        execute_samples_against_model(["prompt"], model.model_id, "key", model.provider_url)


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_raises_on_non_string_message_content(mock_openai: Mock) -> None:
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = Mock(choices=[Mock(message=Mock(content=123))])
    model = ModelInfo.OPENAI_GPT_4O

    with (
        patch("aspis.inferencer.extract_string_output", return_value=123),
        pytest.raises(ValueError, match="Expected message content to be a string"),
    ):
        execute_samples_against_model(["prompt"], model.model_id, "key", model.provider_url)


def test_get_inference_prompt_replaces_placeholder() -> None:
    assert get_inference_prompt("hello", "Judge: <text_to_evaluate/>") == "Judge: <text>hello</text>"


@patch("aspis.inferencer.OpenAI")
def test_evaluate_text_parses_json_and_falls_back_to_raw_output(mock_openai: Mock) -> None:
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content='{"score": 1}'))]),
        Mock(choices=[Mock(message=Mock(content="not-json"))]),
    ]
    model = ModelInfo.OPENAI_GPT_4O

    results = evaluate_text(
        "hello world",
        ["Template A: <text_to_evaluate/>", "Template B: <text_to_evaluate/>"],
        model.model_id,
        "key",
        model.provider_url,
    )

    assert results == [{"score": 1}, {"raw_output": "not-json"}]
    assert mock_client.chat.completions.create.call_count == 2
    mock_client.chat.completions.create.assert_any_call(
        model=model.model_id,
        messages=[{"role": "user", "content": "Template A: <text>hello world</text>"}],
    )
    mock_client.chat.completions.create.assert_any_call(
        model=model.model_id,
        messages=[{"role": "user", "content": "Template B: <text>hello world</text>"}],
    )
