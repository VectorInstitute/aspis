# ruff: noqa

"""Test for chat module."""

import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def cleanup_session_state():
    """Automatically clean up session state after each test."""
    yield

    st.session_state.clear()


# TODO: fix these tests

# @patch("aspis.chat.st.chat_message")
# def test_render_chat_ui_with_empty_conversation(mock_chat_message: Mock) -> None:
#     mock_chat_writer = Mock()
#     mock_chat_message.return_value = mock_chat_writer
#     test_risk_description = "Test risk description"

#     render_chat_ui(openai_api_key="test_api_key", risk_description=test_risk_description)

#     assert mock_chat_message.call_count == 2
#     assert mock_chat_message.call_args_list[0].kwargs["name"] == "assistant"
#     assert (
#         mock_chat_writer.write.call_args_list[0][0][0]
#         == "Hello! I'm your chatbot. Here is the risk description you provided:"
#     )
#     assert mock_chat_message.call_args_list[1].kwargs["name"] == "assistant"
#     assert mock_chat_writer.write.call_args_list[1][0][0] == test_risk_description


# @patch("aspis.chat.st.chat_message")
# def test_render_chat_ui_with_non_empty_conversation(mock_chat_message: Mock) -> None:
#     test_conversation = [
#         ConversationMessage(role=ConversationRole.USER, content="test user message 1"),
#         ConversationMessage(
#             role=ConversationRole.ASSISTANT, content="test assistant message 1"
#         ),
#         ConversationMessage(role=ConversationRole.USER, content="test user message 2"),
#         ConversationMessage(
#             role=ConversationRole.ASSISTANT, content="test assistant message 2"
#         ),
#     ]
#     st.session_state.conversation = test_conversation

#     mock_chat_writer = Mock()
#     mock_chat_message.return_value = mock_chat_writer
#     test_risk_description = "Test risk description"

#     render_chat_ui(openai_api_key="test_api_key", risk_description=test_risk_description)

#     assert mock_chat_message.call_count == len(test_conversation)
#     for i, message in enumerate(test_conversation):
#         assert mock_chat_message.call_args_list[i].kwargs["name"] == message.role.value
#         assert mock_chat_writer.write.call_args_list[i][0][0] == message.content


# @patch("aspis.chat.st.chat_message")
# @patch("aspis.chat.st.chat_input")
# def test_chat_ui_adds_user_input_to_conversation(
#     mock_chat_input: Mock, mock_chat_message: Mock
# ) -> None:
#     mock_chat_writer = Mock()
#     mock_chat_message.return_value = mock_chat_writer
#     test_risk_description = "Test risk description"
#     test_user_input = "test user input"
#     mock_chat_input.return_value = test_user_input

#     render_chat_ui(openai_api_key="test_api_key", risk_description=test_risk_description)

#     mock_chat_input.assert_called_once_with("Your answer...")
#     assert st.session_state.conversation == [
#         ConversationMessage(
#             role=ConversationRole.ASSISTANT,
#             content="Hello! I'm your chatbot. Here is the risk description you provided:",
#         ),
#         ConversationMessage(
#             role=ConversationRole.ASSISTANT, content=test_risk_description
#         ),
#         ConversationMessage(role=ConversationRole.USER, content=test_user_input),
#         ConversationMessage(role=ConversationRole.ASSISTANT, content=test_user_input),
#     ]
