"""Utility functions for the Aspis application."""


def clean_model_output(output: str) -> str:
    """Clean the raw output of the model.

    Args:
        output: The raw output of the model.

    Returns:
        The cleaned output.
    """
    cleaned_output = str(output)
    cleaned_output = cleaned_output.replace("```json", "").replace("```", "")
    return cleaned_output.strip()
