"""Contains the chat functionality for the app."""

from enum import Enum

import streamlit as st


def render_chat_ui(risk_description: str) -> None:
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
        chat_message = st.chat_message(name=message.role.value)
        chat_message.write(message.content)

    # The user's input field
    user_input = st.chat_input("Your answer...")
    if user_input:
        # Writing the user's input to the UI
        conversation.append(
            ConversationMessage(role=ConversationRole.USER, content=user_input)
        )

        # TODO: Here I am just making an "echo" bot. Replace this with the LLM response
        conversation.append(
            ConversationMessage(role=ConversationRole.ASSISTANT, content=user_input)
        )

        # Updating the conversation in the session state
        st.session_state.conversation = conversation
        st.rerun()


class ConversationRole(Enum):
    """The role of a conversation participant."""

    ASSISTANT = "assistant"
    USER = "user"


class ConversationMessage:
    """A message in the conversation."""

    def __init__(self, role: ConversationRole, content: str):
        """Initialize a conversation message with a role and content."""
        self.role = role
        self.content = content

    def __repr__(self) -> str:
        """Return a string representation of the conversation message."""
        return f"{self.role.value}: {self.content}"
