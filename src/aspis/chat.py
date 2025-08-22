"""Contains the chat functionality for the app."""

import streamlit as st

from aspis.chatbot import get_next_chat_question
from aspis.message import ConversationMessage, ConversationRole


def render_chat_ui(
    openai_api_key: str, risk_description: str
) -> list[ConversationMessage] | None:
    """Render the chat UI."""
    conversation = st.session_state.get("conversation", [])

    # Writing the first conversation message if there is none
    if len(conversation) == 0:
        conversation.append(
            ConversationMessage(
                role=ConversationRole.ASSISTANT,
                content="Hello! I'm your chatbot. Here is the risk description you provided:",
            )
        )
        conversation.append(
            ConversationMessage(
                role=ConversationRole.ASSISTANT, content=risk_description
            )
        )

    # Looping through the whole conversation and writing each message to the UI
    # with their respective roles
    for message in conversation:
        write_conversation_message(message)

    # Asking the question
    with st.spinner("Thinking..."):
        question = get_next_chat_question(
            risk_description=risk_description,
            conversation_messages=conversation,
            api_key=openai_api_key,
        )
        if question is None:
            # If there are not more questions to ask, return the conversation history
            # to indicate that the conversation is over
            return conversation

        message = ConversationMessage(role=ConversationRole.ASSISTANT, content=question)
        conversation.append(message)
        write_conversation_message(message)

    # The user's input field for the answer
    user_input = st.chat_input("Your answer...")
    if user_input:
        # Writing the user's input to the UI
        message = ConversationMessage(role=ConversationRole.USER, content=user_input)
        conversation.append(message)
        write_conversation_message(message)

        # Updating the conversation in the session state
        st.session_state.conversation = conversation
        # Triggering a rerun to update the UI and ask the next question
        st.rerun()

    # Returning None to indicate that the conversation is not over yet
    return None


def write_conversation_message(message: ConversationMessage) -> None:
    """
    Write a conversation message to the UI.

    Args:
        message: The conversation message to write.
    """
    chat_message = st.chat_message(name=message.role.value)
    chat_message.write(message.content)
