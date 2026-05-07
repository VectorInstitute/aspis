"""Functions for the programmatic API of the Aspis application."""

import datetime

import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from aspis.inferencer import get_inference_prompt, infer
from aspis.logging import get_logger, setup_logging


app = FastAPI(title="Aspis API")
setup_logging("api")


class EvaluationResponse(BaseModel):
    """Response for the evaluation endpoint.

    Attributes:
        systematized_concept_title: The title of the systematized concept this
            evaluation is for.
        result: The result of the inference of the input text against this
            systematized concept.
        prompt: The prompt that was used to produce the result.
    """

    systematized_concept_title: str
    result: str
    prompt: str


@app.post("/evaluate_from_file")
async def evaluate(
    text_to_evaluate: str = Form(...),
    openai_api_key: str = Form(...),
    systematized_concepts_file: UploadFile = File(...),  # noqa: B008 mypy's false positive on File(...)
) -> list[EvaluationResponse]:
    """
    Evaluate input text against systematized concept prompt templates provided in a YAML file.
    
    Parameters:
        text_to_evaluate (str): The text to evaluate.
        openai_api_key (str): OpenAI API key used for inference.
        systematized_concepts_file (UploadFile): A YAML file containing a top-level `systematized_concepts` key with a list of concepts. Each concept must include `title` and `prompt_template` keys, for example:
            systematized_concepts:
            - title: "Concept 1"
              prompt_template: "Prompt template 1"
            - title: "Concept 2"
              prompt_template: "Prompt template 2"
    
    Returns:
        list[EvaluationResponse]: One EvaluationResponse per concept, with `systematized_concept_title`, the inference `result`, and the resolved `prompt`.
    
    Raises:
        HTTPException: Raised with status 422 for invalid/ malformed YAML or missing required keys, or with status 500 for other evaluation failures.
    """
    logger = get_logger()
    try:
        file_content = await systematized_concepts_file.read()
        file_text = file_content.decode("utf-8")

        systematized_concepts_file_content = yaml.safe_load(file_text)

        assert "systematized_concepts" in systematized_concepts_file_content, (
            "The file must contain a 'systematized_concepts' key"
        )

        systematized_concepts = systematized_concepts_file_content["systematized_concepts"]

        prompt_templates = []
        for systematized_concept in systematized_concepts:
            assert "title" in systematized_concept, "Systematized concepts must contain a 'title' key"
            assert "prompt_template" in systematized_concept, (
                "Systematized concepts must contain a 'prompt_template' key"
            )
            prompt_templates.append(systematized_concept["prompt_template"])

        logger.info("%s: Evaluating input text against all concepts...", datetime.datetime.now())

        results = await infer(text_to_evaluate, prompt_templates, openai_api_key)

        evaluation_responses = []
        for i in range(len(systematized_concepts)):
            evaluation_responses.append(
                EvaluationResponse(
                    systematized_concept_title=systematized_concepts[i]["title"],
                    result=results[i],
                    prompt=get_inference_prompt(text_to_evaluate, systematized_concepts[i]["prompt_template"]),
                )
            )

        return evaluation_responses

    except AssertionError as e:
        logger.exception(f"Assertion error during evaluation: {e}")
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Unexpected error during evaluation: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}") from e
