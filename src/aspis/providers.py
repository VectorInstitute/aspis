"""Model catalog and provider / proxy URL resolution."""

import ipaddress
import socket
from enum import Enum
from typing import Self
from urllib.parse import urlparse


# Hostnames that must never be used as a provider / proxy target.
_BLOCKED_PROVIDER_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata.goog",
    }
)

# Extra IPv4 ranges not always covered by ``ipaddress`` "private" flags.
_BLOCKED_IPV4_NETWORKS = (
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
)

_DANGEROUS_PROVIDER_URL_MESSAGE = "Proxy address must not target a private, local, or link-local network."


class ModelInfo(str, Enum):
    """Information about the supported models for inferencing."""

    model_id: str
    friendly_name: str
    provider_url: str

    OPENAI_GPT_4O = ("gpt-4o", "GPT-4o (OpenAI)", "https://api.openai.com/v1")
    OPENAI_GPT_5_5 = ("gpt-5.5", "GPT-5.5 (OpenAI)", "https://api.openai.com/v1")
    OPENAI_GPT_5_4_MINI = ("gpt-5.4-mini", "GPT-5.4-mini (OpenAI)", "https://api.openai.com/v1")
    GOOGLE_GEMINI_3_1_PRO_PREVIEW = (
        "gemini-3.1-pro-preview",
        "Gemini 3.1 Pro Preview (Google)",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    GOOGLE_GEMINI_3_FLASH_PREVIEW = (
        "gemini-3-flash-preview",
        "Gemini 3 Flash Preview (Google)",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    ANTHROPIC_CLAUDE_4_7_OPUS = ("claude-opus-4-7", "Claude Opus 4.7 (Anthropic)", "https://api.anthropic.com/v1/")
    ANTHROPIC_CLAUDE_4_6_SONNET = (
        "claude-sonnet-4-6",
        "Claude Sonnet 4.6 (Anthropic)",
        "https://api.anthropic.com/v1/",
    )

    def __new__(cls, model_id: str, friendly_name: str, provider_url: str) -> Self:
        """Make a new ModelInfo enum object.

        The value of the enum will be the model ID.

        Args:
            model_id: The ID of the model.
            friendly_name: The friendly name of the model (displayed in the UI).
            provider_url: The OpenAI-compatible base URL for this model's provider.
        """
        obj = str.__new__(cls, model_id)
        obj._value_ = model_id
        obj.model_id = model_id
        obj.friendly_name = friendly_name
        obj.provider_url = provider_url
        return obj

    def __str__(self) -> str:
        """Return the friendly name of the model.

        Returns:
            The friendly name of the model.
        """
        return self.friendly_name

    @classmethod
    def from_model_id(cls, model_id: str) -> Self | None:
        """Return the ModelInfo for an exact model ID match, or None if unknown.

        Args:
            model_id: The model ID to look up.

        Returns:
            The matching ModelInfo, or None when the ID is not a known enum value.
        """
        for member in cls:
            if member.model_id == model_id:
                return member
        return None


def _is_dangerous_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True when ``ip`` is unsuitable as a provider / proxy destination."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    if isinstance(ip, ipaddress.IPv4Address):
        for network in _BLOCKED_IPV4_NETWORKS:
            if ip in network:
                return True

    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )


def assert_provider_url_not_dangerous(provider_url: str) -> None:
    """Raise if ``provider_url`` points at a dangerous / non-public destination.

    Blocks loopback, link-local (including cloud metadata), private RFC1918,
    IPv6 ULA, CGNAT, multicast/reserved/unspecified addresses, and well-known
    local or metadata hostnames. Hostnames are DNS-resolved and every returned
    address is checked.

    Args:
        provider_url: A provider / proxy base URL that has already passed basic
            http(s) URL validation.

    Raises:
        ValueError: If the host is blocked or cannot be resolved safely.
    """
    hostname = urlparse(provider_url.strip()).hostname
    if hostname is None:
        raise ValueError("Please enter a valid proxy address URL (http or https).")

    hostname = hostname.lower().rstrip(".")
    if hostname in _BLOCKED_PROVIDER_HOSTNAMES or hostname.endswith(".localhost"):
        raise ValueError(_DANGEROUS_PROVIDER_URL_MESSAGE)

    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if _is_dangerous_ip(literal_ip):
            raise ValueError(_DANGEROUS_PROVIDER_URL_MESSAGE)
        return

    try:
        addrinfo = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as e:
        raise ValueError(f"Unable to resolve proxy address host '{hostname}'.") from e

    if not addrinfo:
        raise ValueError(f"Unable to resolve proxy address host '{hostname}'.")

    for entry in addrinfo:
        resolved_ip = ipaddress.ip_address(entry[4][0])
        if _is_dangerous_ip(resolved_ip):
            raise ValueError(_DANGEROUS_PROVIDER_URL_MESSAGE)


def validate_provider_url(provider_url: str) -> None:
    """Validate a non-empty provider / proxy base URL.

    Args:
        provider_url: The provider base URL to validate.

    Raises:
        ValueError: If the URL is not a valid http(s) URL with a host, or if it
            targets a private / local / link-local destination.
    """
    parsed = urlparse(provider_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Please enter a valid proxy address URL (http or https).")

    assert_provider_url_not_dangerous(provider_url)


def resolve_model_and_provider_url(
    model: str,
    proxy_base_url: str | None = None,
) -> tuple[str, str]:
    """Return ``(model_id, provider_url)``.

    Known models use their ``provider_url`` when proxy is empty.
    A non-empty proxy overrides (and is URL-validated).
    Custom model IDs require a non-empty valid proxy.

    Args:
        model: Model ID string (known or custom).
        proxy_base_url: Optional OpenAI-compatible base URL override. Leave empty
            for known models to use their provider default. Required for custom
            model IDs.

    Returns:
        A tuple of ``(model_id, provider_url)``.

    Raises:
        ValueError: If a custom model has no proxy, or the proxy URL is invalid.
    """
    model_id = model.strip()
    proxy = proxy_base_url.strip() if proxy_base_url else ""

    if proxy:
        validate_provider_url(proxy)
        return model_id, proxy

    known_model = ModelInfo.from_model_id(model_id)
    if known_model is not None:
        return known_model.model_id, known_model.provider_url

    raise ValueError("Please enter a proxy address for custom model IDs.")
