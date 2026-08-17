"""Manual test case for the inferencer."""

import os

from aspis.inferencer import execute_samples_against_model
from aspis.providers import ModelInfo
from aspis.systematization import SYSTEMATIZATION_PAPER_PATH, SYSTEMATIZATION_PROMPT


def run_inferencer_manual_test() -> None:
    """Run the inferencer manual test."""
    model = ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW
    api_key = os.getenv("ASPIS_API_KEY") or os.getenv("OPENAI_API_KEY")
    assert api_key is not None, "Set ASPIS_API_KEY or OPENAI_API_KEY before running this manual test"

    prompt = SYSTEMATIZATION_PROMPT.format(
        product_description="this is my product",
        risk_description="this is my risk",
        systematization_paper=SYSTEMATIZATION_PAPER_PATH.read_text(),
    )

    model_outputs = execute_samples_against_model(
        [prompt],
        model.model_id,
        api_key,
        model.provider_url,
    )

    print(model_outputs)


if __name__ == "__main__":
    run_inferencer_manual_test()
