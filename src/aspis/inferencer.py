"""Scorer for applications using Aspis as anLLM-as-a-judge."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory

from inspect_ai import Task
from inspect_ai import eval as inspect_ai_eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.log import EvalLog
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate

from aspis.logging import get_logger


INFERENCE_MODEL = "openai/gpt-4o"


async def infer(input_text: str, prompt_templates: list[str], api_key: str) -> list[str]:
    """
    Generate model outputs by applying prompt templates to the input text and evaluating them with the configured inference model.
    
    Each prompt template must contain the placeholder "<text_to_evaluate/>"; that placeholder will be replaced with "<text>{input_text}</text>" before evaluation. The returned list of strings is aligned with the order of prompt_templates.
    
    Parameters:
        input_text (str): Text to inject into each prompt template.
        prompt_templates (list[str]): Prompt templates containing the "<text_to_evaluate/>" placeholder.
        api_key (str): API key used for the evaluation run.
    
    Returns:
        list[str]: Model output strings corresponding to each prompt template.
    
    Raises:
        ValueError: If the evaluation run reports a non-"success" status.
    """
    samples = []
    for prompt_template in prompt_templates:
        input_prompt = get_inference_prompt(input_text, prompt_template)
        samples.append(Sample(input=input_prompt, target=""))

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            run_eval,
            samples,
            api_key,
        )

    assert len(result) == 1, "Expected exactly one result"

    if result[0].status != "success":
        logger = get_logger()
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


def run_eval(samples: list[Sample], api_key: str) -> list[EvalLog]:
    """Helper function to run eval on a list of samples with a specific API key.

    Args:
        samples: The list of samples to run the eval on.
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
        return inspect_ai_eval(task, model=INFERENCE_MODEL, log_dir=temp_dir)


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
