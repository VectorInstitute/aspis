"""Tests for the inferencer module."""

import socket
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from aspis.inferencer import (
    DEFAULT_OPENAI_TIMEOUT_SECONDS,
    ModelInfo,
    assert_provider_url_not_dangerous,
    create_openai_client,
    execute_samples_against_model,
    extract_string_output,
    resolve_model_and_provider_url,
    validate_provider_url,
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


def test_model_info_provider_urls() -> None:
    assert ModelInfo.OPENAI_GPT_4O.provider_url == "https://api.openai.com/v1"
    assert ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW.provider_url == (
        "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    assert ModelInfo.ANTHROPIC_CLAUDE_4_6_SONNET.provider_url == "https://api.anthropic.com/v1/"


def test_model_info_from_model_id() -> None:
    assert ModelInfo.from_model_id("gpt-4o") == ModelInfo.OPENAI_GPT_4O
    assert ModelInfo.from_model_id("not-a-real-model") is None


def test_validate_provider_url_accepts_http_https() -> None:
    with patch("aspis.inferencer.socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 0))]):
        validate_provider_url("https://example.com/v1")
        validate_provider_url("http://example.com:8080/v1")


def test_validate_provider_url_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="Please enter a valid proxy address URL"):
        validate_provider_url("not a url")
    with pytest.raises(ValueError, match="Please enter a valid proxy address URL"):
        validate_provider_url("ftp://example.com/v1")


@pytest.mark.parametrize(
    "provider_url",
    [
        "http://127.0.0.1/v1",
        "http://127.0.0.1:8080/v1",
        "http://localhost/v1",
        "http://localhost:8080/v1",
        "http://foo.localhost/v1",
        "http://[::1]/v1",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/v1",
        "http://192.168.1.1/v1",
        "http://172.16.0.1/v1",
        "http://100.64.0.1/v1",
        "http://0.0.0.0/v1",
        "http://metadata.google.internal/v1",
        "http://[fc00::1]/v1",
        "http://[fe80::1]/v1",
    ],
)
def test_assert_provider_url_not_dangerous_rejects_private_targets(provider_url: str) -> None:
    with pytest.raises(ValueError, match="must not target a private, local, or link-local network"):
        assert_provider_url_not_dangerous(provider_url)


def test_assert_provider_url_not_dangerous_rejects_hostname_resolving_to_private_ip() -> None:
    with (
        patch(
            "aspis.inferencer.socket.getaddrinfo",
            return_value=[(None, None, None, None, ("10.1.2.3", 0))],
        ),
        pytest.raises(ValueError, match="must not target a private, local, or link-local network"),
    ):
        assert_provider_url_not_dangerous("https://evil.example/v1")


def test_assert_provider_url_not_dangerous_accepts_public_hostname() -> None:
    with patch(
        "aspis.inferencer.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("93.184.216.34", 0))],
    ):
        assert_provider_url_not_dangerous("https://proxy.vectorinstitute.ai/v1")


def test_assert_provider_url_not_dangerous_rejects_unresolvable_host() -> None:
    with (
        patch("aspis.inferencer.socket.getaddrinfo", side_effect=socket.gaierror("boom")),
        pytest.raises(ValueError, match="Unable to resolve proxy address host"),
    ):
        assert_provider_url_not_dangerous("https://does-not-resolve.example/v1")


def test_validate_provider_url_rejects_dangerous_destinations() -> None:
    with pytest.raises(ValueError, match="must not target a private, local, or link-local network"):
        validate_provider_url("http://169.254.169.254/")
    with pytest.raises(ValueError, match="must not target a private, local, or link-local network"):
        validate_provider_url("http://localhost:8080/v1")


def test_resolve_model_and_provider_url_known_model_default() -> None:
    model_id, provider_url = resolve_model_and_provider_url(ModelInfo.OPENAI_GPT_4O.model_id)
    assert model_id == ModelInfo.OPENAI_GPT_4O.model_id
    assert provider_url == ModelInfo.OPENAI_GPT_4O.provider_url

    model_id, provider_url = resolve_model_and_provider_url(ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW.model_id, "   ")
    assert model_id == ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW.model_id
    assert provider_url == ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW.provider_url


def test_resolve_model_and_provider_url_known_model_override() -> None:
    model_id, provider_url = resolve_model_and_provider_url(
        ModelInfo.OPENAI_GPT_4O.model_id,
        "https://1.1.1.1/v1",
    )
    assert model_id == ModelInfo.OPENAI_GPT_4O.model_id
    assert provider_url == "https://1.1.1.1/v1"


def test_resolve_model_and_provider_url_custom_model_requires_proxy() -> None:
    with pytest.raises(ValueError, match="Please enter a proxy address for custom model IDs"):
        resolve_model_and_provider_url("my-custom-model")


def test_resolve_model_and_provider_url_custom_model_with_proxy() -> None:
    model_id, provider_url = resolve_model_and_provider_url(
        "my-custom-model",
        "https://1.1.1.1/v1",
    )
    assert model_id == "my-custom-model"
    assert provider_url == "https://1.1.1.1/v1"


def test_resolve_model_and_provider_url_rejects_invalid_url() -> None:
    with pytest.raises(ValueError, match="Please enter a valid proxy address URL"):
        resolve_model_and_provider_url(ModelInfo.OPENAI_GPT_4O.model_id, "not-a-url")


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
