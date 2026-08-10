"""Scorer for applications using Aspis as an LLM-as-a-judge."""

import json
import os
from enum import Enum
from typing import Any, Self

from openai import OpenAI

from aspis.logging import logger
from aspis.utils import clean_model_output


DEFAULT_PROXY_BASE_URL = "https://proxy.vectorinstitute.ai/v1"

# Content part types that are reasoning / thinking (not the final answer).
_REASONING_PART_TYPES = frozenset({"reasoning", "thinking", "reasoning_content"})


class ModelInfo(str, Enum):
    """Information about the supported models for inferencing."""

    model_id: str
    friendly_name: str
    api_key_name: str

    OPENAI_GPT_4O = ("openai/gpt-4o", "GPT-4o (OpenAI)", "OPENAI_API_KEY")
    OPENAI_GPT_5_5 = ("openai/gpt-5.5", "GPT-5.5 (OpenAI)", "OPENAI_API_KEY")
    OPENAI_GPT_5_4_MINI = ("openai/gpt-5.4-mini", "GPT-5.4-mini (OpenAI)", "OPENAI_API_KEY")
    GOOGLE_GEMINI_3_1_PRO_PREVIEW = (
        "google/gemini-3.1-pro-preview",
        "Gemini 3.1 Pro Preview (Google)",
        "GOOGLE_API_KEY",
    )
    GOOGLE_GEMINI_3_FLASH_PREVIEW = (
        "google/gemini-3-flash-preview",
        "Gemini 3 Flash Preview (Google)",
        "GOOGLE_API_KEY",
    )
    GOOGLE_GEMINI_3_1_FLASH_LITE = ("google/gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite (Google)", "GOOGLE_API_KEY")
    ANTHROPIC_CLAUDE_4_7_OPUS = ("anthropic/claude-opus-4-7", "Claude Opus 4.7 (Anthropic)", "ANTHROPIC_API_KEY")
    ANTHROPIC_CLAUDE_4_6_SONNET = ("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6 (Anthropic)", "ANTHROPIC_API_KEY")
    ANTHROPIC_CLAUDE_4_5_HAIKU = (
        "anthropic/claude-haiku-4-5-20251001",
        "Claude Haiku 4.5(Anthropic)",
        "ANTHROPIC_API_KEY",
    )

    def __new__(cls, model_id: str, friendly_name: str, api_key_name: str) -> Self:
        """Make a new ModelInfo enum object.

        The value of the enum will be the model ID.

        Args:
            model_id: The ID of the model.
            friendly_name: The friendly name of the model (displayed in the UI).
            api_key_name: The name of the API key to use to connect to the model.
        """
        obj = str.__new__(cls, model_id)
        obj._value_ = model_id
        obj.model_id = model_id
        obj.friendly_name = friendly_name
        obj.api_key_name = api_key_name
        return obj

    def __str__(self) -> str:
        """Return the friendly name of the model.

        Returns:
            The friendly name of the model.
        """
        return self.friendly_name


def get_proxy_base_url() -> str:
    """Return the OpenAI-compatible proxy base URL.

    Returns:
        The proxy base URL, overridable via ``ASPIS_OPENAI_BASE_URL``.
    """
    return os.environ.get("ASPIS_OPENAI_BASE_URL", DEFAULT_PROXY_BASE_URL)


def create_openai_client(api_key: str) -> OpenAI:
    """Create a new OpenAI client for a single request.

    The API key is passed only to this client instance and is never written to
    process environment variables, so concurrent callers cannot override each
    other's credentials.

    Args:
        api_key: The caller-provided API key.

    Returns:
        A new ``OpenAI`` client pointed at the Vector proxy.
    """
    return OpenAI(api_key=api_key, base_url=get_proxy_base_url())


def execute_samples_against_model(prompts: list[str], model_info: ModelInfo, api_key: str) -> list[str]:
    """Executes a list of prompts against a model and returns the model outputs.

    Args:
        prompts: The list of prompt strings to execute against the model.
        model_info: The information about the model to execute the prompts against.
        api_key: The API key to use to execute the prompts against the model.

    Returns:
        The model outputs.
    """
    logger.info(f"Making API call to model {model_info.model_id}...")

    model_outputs = []
    with create_openai_client(api_key) as client:
        for prompt in prompts:
            try:
                response = client.chat.completions.create(
                    model=model_info.model_id,
                    messages=[{"role": "user", "content": prompt}],
                )
            except Exception as e:
                logger.exception("Error during model evaluation for model %s", model_info.model_id)
                raise ValueError("Error during evaluation.") from e

            if not response.choices:
                raise ValueError("Expected at least one choice in the model response")

            message_content = extract_string_output(response.choices[0].message.content)
            if not isinstance(message_content, str):
                raise ValueError("Expected message content to be a string")
            model_outputs.append(message_content)

    return model_outputs


def evaluate_text(
    input_text: str, prompt_templates: list[str], model_info: ModelInfo, api_key: str
) -> list[dict[str, Any]]:
    """Evaluates input text using the model and the prompt.

    Will use `get_inference_prompt` function to replace placeholders in the prompt
    with the input text.

    Args:
        input_text: The input text to infer.
        prompt_templates: The list of prompt templates to use to infer the input text.
        model_info: The information about the model to use to infer the input text.
        api_key: The API key to use to connect to the model.

    Returns:
        The inferred output from the model, parsed from a json to a dictionary.
    """
    prompts = [get_inference_prompt(input_text, prompt_template) for prompt_template in prompt_templates]
    model_outputs = execute_samples_against_model(prompts, model_info, api_key)

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
