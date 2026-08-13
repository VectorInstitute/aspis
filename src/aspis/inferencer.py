"""Scorer for applications using Aspis as an LLM-as-a-judge."""

import json
import os
from enum import Enum
from typing import Any, Self
from urllib.parse import urlparse

from openai import OpenAI

from aspis.logging import logger
from aspis.utils import clean_model_output


# Power-user override (e.g. Vector). Not used as the public default for known models.
DEFAULT_PROXY_BASE_URL = "https://proxy.vectorinstitute.ai/v1"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 120.0

# Content part types that are reasoning / thinking (not the final answer).
_REASONING_PART_TYPES = frozenset({"reasoning", "thinking", "reasoning_content"})


class Provider(str, Enum):
    """LLM provider for OpenAI-compatible endpoints."""

    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"


PROVIDER_DEFAULT_BASE_URLS: dict[Provider, str] = {
    Provider.OPENAI: "https://api.openai.com/v1",
    Provider.GOOGLE: "https://generativelanguage.googleapis.com/v1beta/openai/",
    Provider.ANTHROPIC: "https://api.anthropic.com/v1/",
}


class ModelInfo(str, Enum):
    """Information about the supported models for inferencing."""

    model_id: str
    friendly_name: str
    provider: Provider

    OPENAI_GPT_4O = ("gpt-4o", "GPT-4o (OpenAI)", Provider.OPENAI)
    OPENAI_GPT_5_5 = ("gpt-5.5", "GPT-5.5 (OpenAI)", Provider.OPENAI)
    OPENAI_GPT_5_4_MINI = ("gpt-5.4-mini", "GPT-5.4-mini (OpenAI)", Provider.OPENAI)
    GOOGLE_GEMINI_3_1_PRO_PREVIEW = ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview (Google)", Provider.GOOGLE)
    GOOGLE_GEMINI_3_FLASH_PREVIEW = ("gemini-3-flash-preview", "Gemini 3 Flash Preview (Google)", Provider.GOOGLE)
    ANTHROPIC_CLAUDE_4_7_OPUS = ("claude-opus-4-7", "Claude Opus 4.7 (Anthropic)", Provider.ANTHROPIC)
    ANTHROPIC_CLAUDE_4_6_SONNET = ("claude-sonnet-4-6", "Claude Sonnet 4.6 (Anthropic)", Provider.ANTHROPIC)

    def __new__(cls, model_id: str, friendly_name: str, provider: Provider) -> Self:
        """Make a new ModelInfo enum object.

        The value of the enum will be the model ID.

        Args:
            model_id: The ID of the model.
            friendly_name: The friendly name of the model (displayed in the UI).
            provider: The provider that hosts this model.
        """
        obj = str.__new__(cls, model_id)
        obj._value_ = model_id
        obj.model_id = model_id
        obj.friendly_name = friendly_name
        obj.provider = provider
        return obj

    def __str__(self) -> str:
        """Return the friendly name of the model.

        Returns:
            The friendly name of the model.
        """
        return self.friendly_name

    @property
    def default_proxy_base_url(self) -> str:
        """Return the provider default OpenAI-compatible base URL for this model."""
        return PROVIDER_DEFAULT_BASE_URLS[self.provider]

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


def validate_proxy_base_url(proxy_base_url: str) -> None:
    """Validate a non-empty proxy base URL.

    Empty strings are not validated; callers should skip this when the value is empty.

    Args:
        proxy_base_url: The proxy base URL to validate.

    Raises:
        ValueError: If the URL is not a valid http(s) URL with a host.
    """
    parsed = urlparse(proxy_base_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid proxy_base_url: {proxy_base_url}")


def resolve_proxy_base_url(
    proxy_base_url: str | None = None,
    model: ModelInfo | str | None = None,
) -> str:
    """Resolve the effective OpenAI-compatible base URL.

    Resolution order:
    1. Non-empty request ``proxy_base_url``
    2. ``ASPIS_OPENAI_BASE_URL`` environment variable
    3. Provider default for a known ``ModelInfo``

    Args:
        proxy_base_url: Optional per-request override.
        model: Known ``ModelInfo`` or free-form model ID for provider default lookup.

    Returns:
        The resolved base URL.

    Raises:
        ValueError: If no override is set and the model is not a known ``ModelInfo``.
    """
    if proxy_base_url is not None and proxy_base_url.strip():
        return proxy_base_url.strip()

    env_url = os.environ.get("ASPIS_OPENAI_BASE_URL")
    if env_url is not None and env_url.strip():
        return env_url.strip()

    model_info = model if isinstance(model, ModelInfo) else ModelInfo.from_model_id(model) if model else None
    if model_info is not None:
        return model_info.default_proxy_base_url

    raise ValueError(
        "proxy_base_url is required when model is not a known ModelInfo value and ASPIS_OPENAI_BASE_URL is not set"
    )


def create_openai_client(
    api_key: str,
    *,
    proxy_base_url: str | None = None,
    model: ModelInfo | str | None = None,
) -> OpenAI:
    """Create a new OpenAI client for a single request.

    The API key is passed only to this client instance and is never written to
    process environment variables, so concurrent callers cannot override each
    other's credentials.

    Args:
        api_key: The caller-provided API key.
        proxy_base_url: Optional per-request OpenAI-compatible base URL override.
        model: Known model or free-form model ID used to resolve the provider default.

    Returns:
        A new ``OpenAI`` client pointed at the resolved base URL.
    """
    return OpenAI(
        api_key=api_key,
        base_url=resolve_proxy_base_url(proxy_base_url=proxy_base_url, model=model),
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


def resolve_model_id(model: ModelInfo | str) -> str:
    """Return the model ID string for a known or free-form model."""
    return model.model_id if isinstance(model, ModelInfo) else model


def execute_samples_against_model(
    prompts: list[str],
    model_info: ModelInfo | str,
    api_key: str,
    proxy_base_url: str | None = None,
) -> list[str]:
    """Executes a list of prompts against a model and returns the model outputs.

    Args:
        prompts: The list of prompt strings to execute against the model.
        model_info: Known ``ModelInfo`` or free-form model ID string.
        api_key: The API key to use to execute the prompts against the model.
        proxy_base_url: Optional per-request OpenAI-compatible base URL override.

    Returns:
        The model outputs.
    """
    model_id = resolve_model_id(model_info)
    logger.info(f"Making API call to model {model_id}...")

    model_outputs = []
    with create_openai_client(api_key, proxy_base_url=proxy_base_url, model=model_info) as client:
        for prompt in prompts:
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                )
            except Exception as e:
                logger.exception("Error during model evaluation for model %s", model_id)
                raise ValueError("Error during evaluation.") from e

            if not response.choices:
                raise ValueError("Expected at least one choice in the model response")

            message_content = extract_string_output(response.choices[0].message.content)
            if not isinstance(message_content, str):
                raise ValueError("Expected message content to be a string")
            model_outputs.append(message_content)

    return model_outputs


def evaluate_text(
    input_text: str,
    prompt_templates: list[str],
    model_info: ModelInfo | str,
    api_key: str,
    proxy_base_url: str | None = None,
) -> list[dict[str, Any]]:
    """Evaluates input text using the model and the prompt.

    Will use `get_inference_prompt` function to replace placeholders in the prompt
    with the input text.

    Args:
        input_text: The input text to infer.
        prompt_templates: The list of prompt templates to use to infer the input text.
        model_info: Known ``ModelInfo`` or free-form model ID string.
        api_key: The API key to use to connect to the model.
        proxy_base_url: Optional per-request OpenAI-compatible base URL override.

    Returns:
        The inferred output from the model, parsed from a json to a dictionary.
    """
    prompts = [get_inference_prompt(input_text, prompt_template) for prompt_template in prompt_templates]
    model_outputs = execute_samples_against_model(prompts, model_info, api_key, proxy_base_url=proxy_base_url)

    parsed_model_outputs = []
    for model_output in model_outputs:
        cleaned_message_content = clean_model_output(model_output)
        try:
            parsed_message_content = json.loads(cleaned_message_content)
        except Exception:
            logger.exception("Error parsing the model output as json. Writing the raw output to the return.")
            logger.debug("Cleaned message content: %s", cleaned_message_content)
            parsed_message_content = {"raw_output": cleaned_message_content}

        parsed_model_outputs.append(parsed_message_content)

    return parsed_model_outputs


def get_inference_prompt(input_text: str, prompt: str) -> str:
    """Get the inference prompt to be used as input to the model.

    It does so by replacing the `<text_to_evaluate/>` placeholder in the prompt
    with `<text>{input_text}</text>`.

    Args:
        input_text: The input text to infer.
        prompt: The prompt to use to infer the input text.

    Returns:
        The inference prompt.
    """
    return prompt.replace("<text_to_evaluate/>", f"<text>{input_text}</text>")


def _part_type(part: Any) -> str | None:
    """Return the content-part type string when available."""
    if isinstance(part, dict):
        part_type = part.get("type")
        return str(part_type) if part_type is not None else None
    part_type = getattr(part, "type", None)
    return str(part_type) if part_type is not None else None


def _part_text(part: Any) -> str | None:
    """Return text from a content part, if present."""
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        text = part.get("text")
        return str(text) if text is not None else None
    text = getattr(part, "text", None)
    return str(text) if text is not None else None


def extract_string_output(model_output: Any) -> str:
    """Extract the answer string from an OpenAI chat completion message content.

    For multi-part content (e.g. reasoning + answer), skips known reasoning part
    types and returns the final remaining text part so JSON parsing is not broken
    by reasoning prefixes.

    Args:
        model_output: The message content from the model response.

    Returns:
        The string output.
    """
    if isinstance(model_output, str):
        return model_output

    if isinstance(model_output, list):
        answer_parts: list[str] = []
        for part in model_output:
            if _part_type(part) in _REASONING_PART_TYPES:
                continue
            text = _part_text(part)
            if text is not None:
                answer_parts.append(text)
        if answer_parts:
            return answer_parts[-1]

    raise ValueError(f"Unsupported model output content type: {type(model_output)}")
