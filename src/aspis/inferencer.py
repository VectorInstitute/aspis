"""Scorer for applications using Aspis as anLLM-as-a-judge."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from typing import Any

from inspect_ai import Task
from inspect_ai import eval as inspect_ai_eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.log import EvalLog
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate

from aspis.logging import get_logger_level, logger
from aspis.utils import clean_model_output


INFERENCE_MODEL = "openai/gpt-4o"


def execute_samples_against_model(samples: list[Sample], model_name: str, api_key: str) -> list[str]:
    """Executes a list of samples against a model and returns the model outputs.

    Args:
        samples: The list of samples to execute against the model.
        model_name: The name of the model to execute the samples against.
        api_key: The API key to use to execute the samples against the model.

    Returns:
        The model outputs.
    """
    with ThreadPoolExecutor() as executor:
        result = executor.submit(run_eval, samples, model_name, api_key).result()

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
        message_content = sample.output.choices[0].message.content
        assert isinstance(message_content, str), "Expected message content to be a string"
        model_outputs.append(message_content)

    return model_outputs


def evaluate_text(input_text: str, prompt_templates: list[str], model_name: str, api_key: str) -> list[dict[str, Any]]:
    """Evaluates input text using the model and the prompt.

    Will use `get_inference_prompt` function to replace placeholders in the prompt
    with the input text.

    Args:
        input_text: The input text to infer.
        prompt_templates: The list of prompt templates to use to infer the input text.
        model_name: The name of the model to use to infer the input text.
        api_key: The API key to use to connect to the model.

    Returns:
        The inferred output from the model, parsed from a json to a dictionary.
    """
    samples = []
    for prompt_template in prompt_templates:
        input_prompt = get_inference_prompt(input_text, prompt_template)
        samples.append(Sample(input=input_prompt, target=""))

    model_outputs = execute_samples_against_model(samples, model_name, api_key)

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


def run_eval(samples: list[Sample], model_name: str, api_key: str) -> list[EvalLog]:
    """Helper function to run eval on a list of samples with a specific API key.

    Args:
        samples: The list of samples to run the eval on.
        model_name: The name of the model to use for the evaluation.
        api_key: The API key to use to run the eval.

    Returns:
        The result of the eval.
    """
    task = Task(
        dataset=MemoryDataset(samples),
        solver=[generate()],
        scorer=model_graded_qa(),
    )
    with TemporaryDirectory() as temp_dir:
        os.environ["OPENAI_API_KEY"] = api_key
        result = inspect_ai_eval(task, model=model_name, log_dir=temp_dir)
        os.environ.pop("OPENAI_API_KEY", None)

        # Reset the logger level to the default level since inspectai sets it to WARNING
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
