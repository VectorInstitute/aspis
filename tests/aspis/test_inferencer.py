"""Tests for the inferencer module."""

from unittest.mock import Mock

from aspis.inferencer import ModelInfo, extract_string_output


def test_extract_string_output() -> None:
    test_cases = [
        (ModelInfo.OPENAI_GPT_4O, "test score", "test score"),
        (ModelInfo.OPENAI_GPT_5_5, [{}, Mock(text="test score")], "test score"),
        (ModelInfo.OPENAI_GPT_5_4_MINI, [Mock(text="test score")], "test score"),
        (ModelInfo.GOOGLE_GEMINI_3_1_PRO_PREVIEW, [{}, Mock(text="test score")], "test score"),
        (ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW, [{}, Mock(text="test score")], "test score"),
        (ModelInfo.GOOGLE_GEMINI_3_1_FLASH_LITE, [{}, Mock(text="test score")], "test score"),
    ]

    for test_case in test_cases:
        model_info, model_output, expected_output = test_case
        assert extract_string_output(model_output, model_info) == expected_output
