"""Scorer for applications using Aspis as anLLM-as-a-judge."""

import asyncio
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory

from inspect_ai import Task, task
from inspect_ai import eval as inspect_ai_eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.log import EvalLog
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate


async def infer(input_text: str, prompt_templates: list[str], api_key: str) -> list[str]:
    """Infer the input text against the model using the prompt.

    Will use `get_inference_prompt` function to replace placeholders in the prompt
    with the input text.

    Args:
        input_text: The input text to infer.
        prompt_templates: The list of prompt templates to use to infer the input text.
        api_key: The API key to use to infer the input text.

    Returns:
        The inferred output from the model.
    """
    samples = []
    for prompt_template in prompt_templates:
        input_prompt = get_inference_prompt(input_text, prompt_template)
        samples.append(Sample(input=input_prompt, target=""))

    @task
    def model_graded_qa_task() -> Task:
        return Task(
            dataset=MemoryDataset(samples),
            solver=[generate()],
            scorer=model_graded_qa(),
        )

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            run_eval,
            api_key,
            model_graded_qa_task,
        )

    assert len(result) == 1, "Expected exactly one result"
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


def run_eval(api_key: str, task_function: Callable[[], Task]) -> list[EvalLog]:
    """Helper function to run eval on a tyask with a specific API key.

    Args:
        api_key: The API key to use to run the eval.
        task_function: The function that returns the task to run the eval on.

    Returns:
        The result of the eval.
    """
    with TemporaryDirectory() as temp_dir:
        os.environ["OPENAI_API_KEY"] = api_key
        return inspect_ai_eval(task_function(), model="openai/gpt-4o", log_dir=temp_dir)


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
