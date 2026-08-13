"""Tests for the inferencer module."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from aspis.inferencer import (
    DEFAULT_OPENAI_TIMEOUT_SECONDS,
    DEFAULT_PROXY_BASE_URL,
    ModelInfo,
    Provider,
    create_openai_client,
    execute_samples_against_model,
    extract_string_output,
    resolve_model_id,
    resolve_proxy_base_url,
    validate_proxy_base_url,
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


def test_model_info_provider_defaults() -> None:
    assert ModelInfo.OPENAI_GPT_4O.provider == Provider.OPENAI
    assert ModelInfo.OPENAI_GPT_4O.default_proxy_base_url == "https://api.openai.com/v1"
    assert ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW.default_proxy_base_url == (
        "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    assert ModelInfo.ANTHROPIC_CLAUDE_4_6_SONNET.default_proxy_base_url == "https://api.anthropic.com/v1/"
    assert DEFAULT_PROXY_BASE_URL == "https://proxy.vectorinstitute.ai/v1"


def test_model_info_from_model_id() -> None:
    assert ModelInfo.from_model_id("gpt-4o") == ModelInfo.OPENAI_GPT_4O
    assert ModelInfo.from_model_id("not-a-real-model") is None


def test_resolve_model_id() -> None:
    assert resolve_model_id(ModelInfo.OPENAI_GPT_4O) == "gpt-4o"
    assert resolve_model_id("my-custom-model") == "my-custom-model"


def test_validate_proxy_base_url_accepts_http_https() -> None:
    validate_proxy_base_url("https://example.com/v1")
    validate_proxy_base_url("http://localhost:8080/v1")


def test_validate_proxy_base_url_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid proxy_base_url"):
        validate_proxy_base_url("not a url")
    with pytest.raises(ValueError, match="Invalid proxy_base_url"):
        validate_proxy_base_url("ftp://example.com/v1")


def test_resolve_proxy_base_url_request_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASPIS_OPENAI_BASE_URL", "https://env.example/v1")
    assert (
        resolve_proxy_base_url(
            proxy_base_url="https://request.example/v1",
            model=ModelInfo.OPENAI_GPT_4O,
        )
        == "https://request.example/v1"
    )


def test_resolve_proxy_base_url_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASPIS_OPENAI_BASE_URL", "https://env.example/v1")
    assert resolve_proxy_base_url(model=ModelInfo.OPENAI_GPT_4O) == "https://env.example/v1"


def test_resolve_proxy_base_url_provider_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASPIS_OPENAI_BASE_URL", raising=False)
    assert resolve_proxy_base_url(model=ModelInfo.OPENAI_GPT_4O) == ModelInfo.OPENAI_GPT_4O.default_proxy_base_url
    assert (
        resolve_proxy_base_url(model=ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW)
        == ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW.default_proxy_base_url
    )
    assert resolve_proxy_base_url(model="gpt-4o") == ModelInfo.OPENAI_GPT_4O.default_proxy_base_url


def test_resolve_proxy_base_url_custom_model_requires_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASPIS_OPENAI_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="proxy_base_url is required"):
        resolve_proxy_base_url(model="my-custom-model")


def test_resolve_proxy_base_url_ignores_blank_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASPIS_OPENAI_BASE_URL", raising=False)
    assert (
        resolve_proxy_base_url(proxy_base_url="   ", model=ModelInfo.OPENAI_GPT_4O)
        == ModelInfo.OPENAI_GPT_4O.default_proxy_base_url
    )


@patch("aspis.inferencer.OpenAI")
def test_create_openai_client_passes_api_key_and_proxy(mock_openai: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASPIS_OPENAI_BASE_URL", raising=False)
    api_key = "test-api-key"
    create_openai_client(api_key, model=ModelInfo.OPENAI_GPT_4O)

    mock_openai.assert_called_once_with(
        api_key=api_key,
        base_url=ModelInfo.OPENAI_GPT_4O.default_proxy_base_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


@patch("aspis.inferencer.OpenAI")
def test_create_openai_client_request_override(mock_openai: Mock) -> None:
    create_openai_client(
        "key",
        proxy_base_url=DEFAULT_PROXY_BASE_URL,
        model=ModelInfo.OPENAI_GPT_4O,
    )
    mock_openai.assert_called_once_with(
        api_key="key",
        base_url=DEFAULT_PROXY_BASE_URL,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_uses_per_call_client(mock_openai: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASPIS_OPENAI_BASE_URL", raising=False)
    api_key = "caller-api-key"
    model_info = ModelInfo.OPENAI_GPT_4O
    prompts = ["prompt one", "prompt two"]

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content="output one"))]),
        Mock(choices=[Mock(message=Mock(content="output two"))]),
    ]

    outputs = execute_samples_against_model(prompts, model_info, api_key)

    assert outputs == ["output one", "output two"]
    mock_openai.assert_called_once_with(
        api_key=api_key,
        base_url=model_info.default_proxy_base_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
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


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_custom_model_and_proxy(
    mock_openai: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ASPIS_OPENAI_BASE_URL", raising=False)
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.return_value = Mock(choices=[Mock(message=Mock(content="ok"))])

    outputs = execute_samples_against_model(
        ["prompt"],
        "my-custom-model",
        "key",
        proxy_base_url=DEFAULT_PROXY_BASE_URL,
    )

    assert outputs == ["ok"]
    mock_openai.assert_called_once_with(
        api_key="key",
        base_url=DEFAULT_PROXY_BASE_URL,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
    mock_client.chat.completions.create.assert_called_once_with(
        model="my-custom-model",
        messages=[{"role": "user", "content": "prompt"}],
    )


@patch("aspis.inferencer.OpenAI")
def test_execute_samples_against_model_raises_on_api_error(mock_openai: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASPIS_OPENAI_BASE_URL", raising=False)
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.chat.completions.create.side_effect = RuntimeError("boom")

    with pytest.raises(ValueError, match="Error during evaluation") as exc_info:
        execute_samples_against_model(["prompt"], ModelInfo.OPENAI_GPT_4O, "key")

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    mock_openai.assert_called_once_with(
        api_key="key",
        base_url=ModelInfo.OPENAI_GPT_4O.default_proxy_base_url,
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

    with pytest.raises(ValueError, match="Expected at least one choice"):
        execute_samples_against_model(["prompt"], ModelInfo.OPENAI_GPT_4O, "key")
