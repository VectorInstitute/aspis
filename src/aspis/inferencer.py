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

    OPENAI_GPT_4O = ("gpt-4o", "GPT-4o (OpenAI)")
    OPENAI_GPT_5_5 = ("gpt-5.5", "GPT-5.5 (OpenAI)")
    OPENAI_GPT_5_4_MINI = ("gpt-5.4-mini", "GPT-5.4-mini (OpenAI)")
    GOOGLE_GEMINI_3_1_PRO_PREVIEW = ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview (Google)")
    GOOGLE_GEMINI_3_FLASH_PREVIEW = ("gemini-3-flash-preview", "Gemini 3 Flash Preview (Google)")
    ANTHROPIC_CLAUDE_4_7_OPUS = ("claude-opus-4-7", "Claude Opus 4.7 (Anthropic)")
    ANTHROPIC_CLAUDE_4_6_SONNET = ("claude-sonnet-4-6", "Claude Sonnet 4.6 (Anthropic)")

    def __new__(cls, model_id: str, friendly_name: str) -> Self:
        """
        Create a model metadata enum member with its model identifier and display name.
        
        Parameters:
            model_id (str): The model identifier.
            friendly_name (str): The name displayed to users.
        
        Returns:
            ModelInfo: The initialized enum member.
        """
        obj = str.__new__(cls, model_id)
        obj._value_ = model_id
        obj.model_id = model_id
        obj.friendly_name = friendly_name
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
    """
    Execute prompts against a model and collect its responses.
    
    Args:
        prompts: The prompts to submit.
        model_info: The model to use.
        api_key: The API key for the model client.
    
    Returns:
        The model responses in prompt order.
    
    Raises:
        ValueError: If a model request fails, returns no choices, or produces invalid content.
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
    """
    Evaluate input text against prompt templates and parse each model response as JSON.
    
    Parameters:
        input_text (str): Text substituted into each prompt template.
        prompt_templates (list[str]): Templates used to generate evaluation prompts.
    
    Returns:
        list[dict[str, Any]]: Parsed JSON responses, or a dictionary containing
            ``raw_output`` when a response cannot be parsed as JSON.
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
    """
    Extract the final answer text from model response content.
    
    Parameters:
        model_output (Any): A string or multipart response content.
    
    Returns:
        str: The answer text, using the final text part after excluding reasoning parts.
    
    Raises:
        ValueError: If the content is unsupported or contains no text parts.
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
