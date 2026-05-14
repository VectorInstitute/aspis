"""Scorer for applications using Aspis as anLLM-as-a-judge."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Any, Self

from inspect_ai import Task
from inspect_ai import eval as inspect_ai_eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.log import EvalLog
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate

from aspis.logging import get_logger_level, logger
from aspis.utils import clean_model_output


_INSPECTAI_EVAL_LOCK = Lock()


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


def execute_samples_against_model(samples: list[Sample], model_info: ModelInfo, api_key: str) -> list[str]:
    """Executes a list of samples against a model and returns the model outputs.

    Args:
        samples: The list of samples to execute against the model.
        model_info: The information about the model to execute the samples against.
        api_key: The API key to use to execute the samples against the model.

    Returns:
        The model outputs.
    """
    logger.info(f"Making API call to model {model_info.model_id}...")

    # Executing this in a synchronous thread pool executor to make InspectAI
    # work well with streamlit's main thread
    with ThreadPoolExecutor() as executor:
        result = executor.submit(run_eval, samples, model_info, api_key).result()

    assert len(result) == 1, "Expected exactly one result"

    if result[0].status != "success":
        logger.error("Evaluation error: %s", result[0].error)
        logger.debug("Full evaluation result: %s", result[0])
        raise ValueError("Error during evaluation.")

    assert result[0].samples is not None, "Expected samples to be not None"
    assert len(result[0].samples) == len(samples), (
        "Expected number of samples to be the same as the number of samples in the task"
    )

    model_outputs = []
    for sample in result[0].samples:
        message_content = extract_string_output(
            sample.output.choices[0].message.content,
            model_info,
        )
        assert isinstance(message_content, str), "Expected message content to be a string"
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
    samples = []
    for prompt_template in prompt_templates:
        input_prompt = get_inference_prompt(input_text, prompt_template)
        samples.append(Sample(input=input_prompt, target=""))

    model_outputs = execute_samples_against_model(samples, model_info, api_key)

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


def run_eval(samples: list[Sample], model_info: ModelInfo, api_key: str) -> list[EvalLog]:
    """Helper function to run eval on a list of samples with a specific API key.

    Args:
        samples: The list of samples to run the eval on.
        model_info: The information about the model to use for the evaluation.
        api_key: The API key to use to run the eval.

    Returns:
        The result of the eval.
    """
    task = Task(
        dataset=MemoryDataset(samples),
        solver=[generate()],
        scorer=model_graded_qa(),
    )
    with TemporaryDirectory() as temp_dir, _INSPECTAI_EVAL_LOCK:
        try:
            os.environ[model_info.api_key_name] = api_key
            result = inspect_ai_eval(task, model=model_info.model_id, log_dir=temp_dir)
        finally:
            os.environ.pop(model_info.api_key_name, None)
            # Reset the logger level to the default level since
            # inspectai sets it to WARNING
            logger.setLevel(get_logger_level())

    return result


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


def extract_string_output(model_output: Any, model_info: ModelInfo) -> str:
    """Extract the string output from the model output given the model info.

    Args:
        model_output: The model output.
        model_info: The model info.

    Returns:
        The string output.
    """
    if model_info == ModelInfo.OPENAI_GPT_4O:
        return model_output

    if model_info in [
        ModelInfo.OPENAI_GPT_5_5,
        ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW,
        ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW,
        ModelInfo.GOOGLE_GEMINI_3_1_FLASH_LITE,
    ]:
        # first output is the reasoning, second output is the answer
        return model_output[1].text

    if model_info == ModelInfo.OPENAI_GPT_5_4_MINI:
        return model_output[0].text

    raise ValueError(f"Model info {model_info} not supported")
