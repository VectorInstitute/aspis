"""Functions for the programmatic API of the Aspis application."""

import datetime
import logging

import yaml
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

from aspis.scorer import Score, ScorerModel, TaskMetadata, TaskState


app = FastAPI(title="Aspis API")
logger = logging.getLogger("uvicorn.access")


class EvaluationResponse(BaseModel):
    """Response for the evaluation endpoint.

    Attributes:
        systematized_concept_title: The title of the systematized concept this
            evaluation is for.
        evaluation: The evaluation for the input text against this systematized concept.
        task_state: The task state that was used to produce the evaluation.
    """

    systematized_concept_title: str
    evaluation: Score
    task_state: TaskState


@app.post("/evaluate_from_file")
async def evaluate(
    text_to_evaluate: str = Form(...),
    openai_api_key: str = Form(...),
    systematized_concepts_file: UploadFile = File(...),  # noqa: B008 mypy's false positive on File(...)
) -> list[EvaluationResponse]:
    """Evaluate an input text using systematized concepts from a file.

    Returns one evaluation per systematized concept.

    Args:
        text_to_evaluate: The text to evaluate.
        openai_api_key: The OpenAI API key to use the LLM.
        systematized_concepts_file: The file containing the systematized concepts.
            It must be a `.yaml` file that contains a `systematized_concepts` key
            with a list of systematized concepts. Each systematized concept must
            contain a `title` key and a `prompt_template` key. Example:
            \n
                systematized_concepts:
                - title: "Systematized concept 1"
                  prompt_template: "Prompt template 1"
                - title: "Systematized concept 2"
                  prompt_template: "Prompt template 2"

    Returns:
        A list of evaluations for the input text, one for each systematized concept
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

    evaluation_responses = []
    for systematized_concept in systematized_concepts_file_content["systematized_concepts"]:
        assert "title" in systematized_concept, "Systematized concepts must contain a 'title' key"
        assert "prompt_template" in systematized_concept, "Systematized concepts must contain a 'prompt_template' key"

        task_state = TaskState(
            model=scorer_model,
            input=text_to_evaluate,
            user_prompt=systematized_concept["prompt_template"],
            metadata=TaskMetadata(
                value_to_replace="<text_to_evaluate/>",
                text_prefix="<text>",
                text_suffix="</text>",
            ),
        )

        logger.info(
            f"{datetime.datetime.now()}: "
            + f"Evaluating input text against concept '{systematized_concept['title']}'..."
        )
        score = await scorer(task_state)

        evaluation_responses.append(
            EvaluationResponse(
                systematized_concept_title=systematized_concept["title"],
                evaluation=score,
                task_state=task_state,
            )
        )

    return evaluation_responses
