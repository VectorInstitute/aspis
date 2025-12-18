"""Scorer for applications using Aspis as anLLM-as-a-judge."""

from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel

from aspis.model import get_llm


class ScorerModel(Enum):
    """List of supported scorer models."""

    GPT_4O = "gpt-4o"

    def get_scorer_class(self) -> type["Scorer"]:
        """Get the scorer class for the model.

        Returns:
            The scorer class for the model.
        """
        if self == ScorerModel.GPT_4O:
            return OpenAIScorer

        raise ValueError(f"Unsupported scorer model: {self.value}")


class TaskMetadata(BaseModel):
    """Metadata for the task."""

    value_to_replace: str
    text_prefix: str
    text_suffix: str


class TaskState(BaseModel):
    """State of the task.

    Attributes:
        model: Model being used to evaluate the sample.
        input: Input from the Sample, should be considered immutable.
        user_prompt: User prompt for this state.
        metadata: Metadata for the task.
    """

    model: ScorerModel
    input: str
    user_prompt: str
    metadata: TaskMetadata


class Score(BaseModel):
    """Score for the sample.

    Attributes:
        score: Score for the sample.
        explanation: Explanation for the score.
    """

    score: str
    explanation: str


class Scorer(Protocol):
    """Scorer for applications using Aspis as anLLM-as-a-judge."""

    def __init__(self, **kwargs: Any):
        """Initialize the scorer.

        Args:
            **kwargs: Additional arguments for the scorer.
        """
        ...

    async def __call__(self, state: TaskState) -> Score:
        """Score the task.

        Args:
            state: The state of the task.

        Returns:
            The score for the given task state.
        """
        ...


class OpenAIScorer(Scorer):
    """Scorer for applications using OpenAI models."""

    def __init__(self, api_key: str):
        """Initialize an OpenAIScorer.

        Args:
            api_key: The key to be used to call the OpenAI APIs.
        """
        self.api_key = api_key

    async def __call__(self, state: TaskState) -> Score:
        """Score the task.

        Args:
            state: The state of the task.

        Returns:
            The score for the given task state.
        """
        score_prompt = state.user_prompt.replace(
            state.metadata.value_to_replace,
            f"{state.metadata.text_prefix}{state.input}{state.metadata.text_suffix}",
        )

        llm = get_llm(self.api_key)
        response = llm.invoke(score_prompt)

        assert isinstance(response.content, str)
        return Score(score=response.content, explanation=response.content)
