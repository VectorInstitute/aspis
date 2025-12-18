"""Functions for the programmatic API of the Aspis application."""

import yaml
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from aspis.scorer import Score, ScorerModel, TaskMetadata, TaskState


app = FastAPI()


class ScoreResponse(BaseModel):
    """Response for the score endpoint.

    Attributes:
        systematized_concept_title: The title of the systematized concept this
            score is for.
        score: The score for the input text against this systematized concept.
        task_state: The task state that was used to produce the score.
    """

    systematized_concept_title: str
    score: Score
    task_state: TaskState


@app.post("/score_from_file")
async def score(
    text_to_score: str,
    openai_api_key: str,
    systematized_concepts_file: UploadFile = File(...),  # noqa: B008 mypy's false positive on File(...)
) -> list[ScoreResponse]:
    """Score an input text using systematized concepts from a file.

    Returns one score per systematized concept.

    Args:
        text_to_score: The text to score.
        openai_api_key: The OpenAI API key to use the LLM.
        systematized_concepts_file: The file containing the systematized concepts.

    Returns:
        A list of scores for the input text, one for each systematized concept
        in the file.
    """
    file_content = await systematized_concepts_file.read()
    file_text = file_content.decode("utf-8")

    systematized_concepts_file_content = yaml.safe_load(file_text)

    assert "systematized_concepts" in systematized_concepts_file_content, (
        "The file must contain a 'systematized_concepts' key"
    )

    scorer_model = ScorerModel.GPT_4O
    scorer_class = scorer_model.get_scorer_class()
    scorer = scorer_class(api_key=openai_api_key)

    score_responses = []
    for systematized_concept in systematized_concepts_file_content["systematized_concepts"]:
        assert ["title", "prompt_template"] in systematized_concept, (
            "Each systematized concept must contain a 'title' and 'prompt_template' key"
        )

        task_state = TaskState(
            model=scorer_model,
            input=text_to_score,
            user_prompt=systematized_concept["prompt_template"],
            metadata=TaskMetadata(value_to_replace="<text_to_score/>"),
        )

        score = await scorer(task_state)

        score_responses.append(
            ScoreResponse(
                systematized_concept_title=systematized_concept["title"],
                score=score,
                task_state=task_state,
            )
        )

    return score_responses
