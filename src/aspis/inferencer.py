"""Scorer for applications using Aspis as anLLM-as-a-judge."""

from aspis.model import get_llm


def infer(input_text: str, prompt: str, api_key: str) -> str:
    """Infer the input text against the model using the prompt.

    Will use `get_inference_prompt` function to replace placeholders in the prompt
    with the input text.

    Args:
        input_text: The input text to infer.
        prompt: The prompt to use to infer the input text.
        api_key: The API key to use to infer the input text.

    Returns:
        The inferred output from the model.
    """
    llm = get_llm(api_key)
    response = llm.invoke(get_inference_prompt(input_text, prompt))

    assert isinstance(response.content, str)
    return response.content


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
