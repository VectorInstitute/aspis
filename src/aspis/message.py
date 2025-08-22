"""Classes to represent the conversation messages."""

from enum import Enum


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

    def __eq__(self, other: object) -> bool:
        """Check if the conversation message is equal to another object."""
        if not isinstance(other, ConversationMessage):
            return False
        return self.role == other.role and self.content == other.content

    def __hash__(self) -> int:
        """Hash the conversation message."""
        return hash((self.role, self.content))
