"""Functions and classes to call the chatbots for asking questions."""

from langchain.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from aspis.message import ConversationMessage, ConversationRole


CLARIFICATION_PROMPT = ChatPromptTemplate.from_template(
    """
You are an AI risk analyst.
The user has described this AI risk: {risk_description}.

Ask one clarifying question at a time to fully understand:
- What's the purpose of the product
- Which systems are affected
- How severe the risk is
- Possible mitigation strategies
- Who are the affected users
- What's the data we're dealing with
- What's level of autonomy of the AI system

Previous questions and answers so far:
{conversation_history}

Ask your next clarifying question.
Reply with "enough information" once you have enough details to answer all the questions.
"""
)


def get_next_chat_question(
    risk_description: str,
    conversation_messages: list[ConversationMessage],
    api_key: str,
) -> str | None:
    """
    Get the next chat question.

    Args:
        history: The conversation history.

    Returns
    -------
        The next chat question.
    """
    llm = get_llm(api_key)

    conversation_history = format_conversation_messages(conversation_messages)
    response = llm.invoke(
        CLARIFICATION_PROMPT.format(
            risk_description=risk_description, conversation_history=conversation_history
        )
    )

    response_content = response.content
    assert isinstance(response_content, str)

    if "enough information" in response_content.lower():
        # If the response is "enough information", return None
        # to indicate that the conversation is over
        return None

    return response_content


def get_llm(api_key: str) -> BaseChatModel:
    """
    Get the LLM object.

    Returns
    -------
        The LLM.
    """
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key=SecretStr(api_key),
    )


def format_conversation_messages(
    conversation_messages: list[ConversationMessage],
) -> str:
    """
    Format the conversation history.

    Returns
    -------
        The formatted conversation history.
    """
    result = ""
    for conversation_message in conversation_messages:
        role = "Q" if conversation_message.role == ConversationRole.ASSISTANT else "A"
        result += f"{role}: {conversation_message.content}\n"

    return result
