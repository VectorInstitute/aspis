"""Tests for the providers module."""

import socket
from unittest.mock import patch

import pytest

from aspis.providers import (
    ModelInfo,
    assert_provider_url_not_dangerous,
    resolve_model_and_provider_url,
    validate_provider_url,
)


def test_model_info_provider_urls() -> None:
    assert ModelInfo.OPENAI_GPT_4O.provider_url == "https://api.openai.com/v1"
    assert ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW.provider_url == (
        "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    assert ModelInfo.ANTHROPIC_CLAUDE_4_6_SONNET.provider_url == "https://api.anthropic.com/v1/"


def test_model_info_from_model_id() -> None:
    assert ModelInfo.from_model_id("gpt-4o") == ModelInfo.OPENAI_GPT_4O
    assert ModelInfo.from_model_id("not-a-real-model") is None


def test_model_info_str_returns_friendly_name() -> None:
    assert str(ModelInfo.OPENAI_GPT_4O) == "GPT-4o (OpenAI)"


def test_validate_provider_url_accepts_http_https() -> None:
    with patch("aspis.providers.socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 0))]):
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
            "aspis.providers.socket.getaddrinfo",
            return_value=[(None, None, None, None, ("10.1.2.3", 0))],
        ),
        pytest.raises(ValueError, match="must not target a private, local, or link-local network"),
    ):
        assert_provider_url_not_dangerous("https://evil.example/v1")


def test_assert_provider_url_not_dangerous_accepts_public_hostname() -> None:
    with patch(
        "aspis.providers.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("93.184.216.34", 0))],
    ):
        assert_provider_url_not_dangerous("https://proxy.vectorinstitute.ai/v1")


def test_assert_provider_url_not_dangerous_rejects_unresolvable_host() -> None:
    with (
        patch("aspis.providers.socket.getaddrinfo", side_effect=socket.gaierror("boom")),
        pytest.raises(ValueError, match="Unable to resolve proxy address host"),
    ):
        assert_provider_url_not_dangerous("https://does-not-resolve.example/v1")


def test_validate_provider_url_rejects_dangerous_destinations() -> None:
    with pytest.raises(ValueError, match="must not target a private, local, or link-local network"):
        validate_provider_url("http://169.254.169.254/")
    with pytest.raises(ValueError, match="must not target a private, local, or link-local network"):
        validate_provider_url("http://localhost:8080/v1")


def test_assert_provider_url_not_dangerous_rejects_ipv4_mapped_private_address() -> None:
    with pytest.raises(ValueError, match="must not target a private, local, or link-local network"):
        assert_provider_url_not_dangerous("http://[::ffff:127.0.0.1]/v1")


def test_assert_provider_url_not_dangerous_rejects_missing_hostname() -> None:
    with pytest.raises(ValueError, match="Please enter a valid proxy address URL"):
        assert_provider_url_not_dangerous("http:///v1")


def test_assert_provider_url_not_dangerous_rejects_empty_addrinfo() -> None:
    with (
        patch("aspis.providers.socket.getaddrinfo", return_value=[]),
        pytest.raises(ValueError, match="Unable to resolve proxy address host"),
    ):
        assert_provider_url_not_dangerous("https://empty-dns.example/v1")


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
