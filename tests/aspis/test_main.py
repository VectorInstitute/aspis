"""Test for main module."""

from unittest.mock import Mock, patch

import pytest
import streamlit as st

from aspis.main import main


@pytest.fixture(autouse=True)
def cleanup_session_state():
    """Automatically clean up session state after each test."""
    yield

    st.session_state.clear()


@patch("aspis.main.st.text_input")
def test_main_render_api_key_input_when_empty(mock_text_input: Mock) -> None:
    main()

    assert mock_text_input.call_count == 1
    assert (
        mock_text_input.call_args_list[0].kwargs["label"]
        == "Enter your Open AI API key:"
    )


@patch("aspis.main.st.text_area")
def test_main_render_risk_input_when_api_key_is_set(mock_text_area: Mock) -> None:
    st.session_state.openai_api_key = "test api key"

    main()

    assert mock_text_area.call_count == 1
    assert (
        mock_text_area.call_args_list[0].kwargs["label"]
        == "What is the AI risk you want to create a measurement instrument for?"
    )


@patch("aspis.main.render_chat_ui")
def test_main_render_chat_ui_when_api_key_and_risk_description_are_set(
    mock_render_chat_ui: Mock,
) -> None:
    st.session_state.openai_api_key = "test api key"
    st.session_state.risk_description = "test risk description"

    main()

    assert mock_render_chat_ui.call_count == 1
    assert (
        mock_render_chat_ui.call_args_list[0].kwargs["risk_description"]
        == "test risk description"
    )
