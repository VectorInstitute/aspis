"""Test for the main module."""

import json
from copy import deepcopy
from dataclasses import asdict
from io import BytesIO
from typing import Any, Callable
from unittest.mock import ANY, Mock, patch

import pytest
import yaml
from streamlit.testing.v1 import AppTest

from aspis.inferencer import DEFAULT_PROXY_BASE_URL, ModelInfo
from aspis.systematization import (
    SystematizedConcept,
    get_systematization_questions_prompt,
    get_systematized_concepts_prompt,
)


def make_openai_side_effect(api_key: str, return_value: Any) -> Callable[..., Mock]:
    """
    Create a mocked OpenAI client factory for tests.
    
    Parameters:
        api_key (str): API key the mocked client must receive.
        return_value (Any): Value encoded as the mock completion response.
    
    Returns:
        Callable[..., Mock]: A side-effect function that returns a configured mock client.
    """
    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        assert kwargs.get("api_key") == api_key
        assert kwargs.get("base_url") == DEFAULT_PROXY_BASE_URL

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps(return_value)))]
        )
        return mock_client

    return side_effect


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_inputs_when_empty(mock_openai: Mock) -> None:
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    assert app.title[0].value == "🛡️ Aspis"
    assert "api_key" not in app.session_state
    assert "model_info" not in app.session_state
    assert "risk_description" not in app.session_state
    assert "product_description" not in app.session_state

    mock_openai.assert_not_called()
    assert app.selectbox("model_info_input").label == "Select the model you want to use:"
    assert app.selectbox("model_info_input").options == [model.friendly_name for model in list(ModelInfo)]
    assert app.selectbox("model_info_input").index == 0
    assert app.text_input("api_key_input").label == "Enter your API key:"
    assert app.text_area("product_description_input").label == "What is the description of your AI-powered product?"
    assert (
        app.text_area("risk_description_input").label
        == "What is the AI risk you want to create a measurement instrument for?"
    )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_ask_for_questions_when_inputs_are_set(mock_openai: Mock) -> None:
    test_questions = ["test question"]
    test_api_key = "test api key"
    test_model_info = ModelInfo.OPENAI_GPT_4O
    test_risk_description = "test risk description"
    test_product_description = "test product description"

    created_clients: list[Mock] = []

    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        assert kwargs.get("api_key") == test_api_key
        assert kwargs.get("base_url") == DEFAULT_PROXY_BASE_URL
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps(test_questions)))]
        )
        created_clients.append(mock_client)
        return mock_client

    mock_openai.side_effect = side_effect

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.api_key = test_api_key
    app.session_state.model_info = test_model_info
    app.session_state.risk_description = test_risk_description
    app.session_state.product_description = test_product_description

    app.run()

    assert mock_openai.call_count == 1
    mock_openai.assert_called_once_with(api_key=test_api_key, base_url=DEFAULT_PROXY_BASE_URL)
    assert len(created_clients) == 1
    created_clients[0].chat.completions.create.assert_called_once_with(
        model=test_model_info.model_id,
        messages=[
            {
                "role": "user",
                "content": get_systematization_questions_prompt(test_product_description, test_risk_description),
            }
        ],
    )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_error_messages_when_inputs_are_not_set(mock_openai: Mock) -> None:
    test_api_key = "test api key"
    test_risk_description = "test risk description"
    test_product_description = "test product description"
    test_model_info = ModelInfo.OPENAI_GPT_4O
    mock_openai.side_effect = make_openai_side_effect(test_api_key, ["test question"])

    # Empty API key
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()
    app.selectbox("model_info_input").set_value(test_model_info)
    app.text_input("api_key_input").set_value("")
    app.text_area("product_description_input").set_value(test_product_description)
    app.text_area("risk_description_input").set_value(test_risk_description)

    app.button("generate_questions_button").click()
    app.run()

    assert app.error[0].value == "Please enter an API key before proceeding."

    # Empty risk description
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()
    app.selectbox("model_info_input").set_value(test_model_info)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("risk_description_input").set_value("")
    app.text_area("product_description_input").set_value(test_product_description)

    app.button("generate_questions_button").click()
    app.run()

    assert app.error[0].value == "Please enter a risk description before proceeding."

    # Empty product description
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("risk_description_input").set_value(test_risk_description)
    app.text_area("product_description_input").set_value("")

    app.button("generate_questions_button").click()
    app.run()

    assert app.error[0].value == "Please enter a product description before proceeding."

    # All inputs are set
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()
    app.selectbox("model_info_input").set_value(test_model_info)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("risk_description_input").set_value(test_risk_description)
    app.text_area("product_description_input").set_value(test_product_description)

    app.run()

    app.button("generate_questions_button").click()
    app.run()

    assert len(app.error) == 0
    assert app.session_state.api_key == test_api_key
    assert app.session_state.model_info == test_model_info
    assert app.session_state.risk_description == test_risk_description
    assert app.session_state.product_description == test_product_description
    mock_openai.assert_called()


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_error_when_questions_are_none(mock_openai: Mock) -> None:
    test_api_key = "test api key"
    test_risk_description = "test risk description"
    test_product_description = "test product description"
    test_model_info = ModelInfo.OPENAI_GPT_4O
    mock_openai.side_effect = make_openai_side_effect(test_api_key, None)

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    app.selectbox("model_info_input").set_value(test_model_info)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("risk_description_input").set_value(test_risk_description)
    app.text_area("product_description_input").set_value(test_product_description)

    app.button("generate_questions_button").click()
    app.run()

    assert mock_openai.call_count == 1
    mock_openai.assert_called_once_with(api_key=test_api_key, base_url=DEFAULT_PROXY_BASE_URL)
    assert app.error[0].value == "Error generating questions. Please try again."


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_questions_on_success(mock_openai: Mock) -> None:
    test_questions = ["test question 1", "test question 2"]
    test_api_key = "test api key"
    test_model_info = ModelInfo.OPENAI_GPT_4O
    test_product_description = "test product description"
    test_risk_description = "test risk description"

    created_clients: list[Mock] = []

    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        assert kwargs.get("api_key") == test_api_key
        assert kwargs.get("base_url") == DEFAULT_PROXY_BASE_URL
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps(test_questions)))]
        )
        created_clients.append(mock_client)
        return mock_client

    mock_openai.side_effect = side_effect

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    app.selectbox("model_info_input").set_value(test_model_info)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("product_description_input").set_value(test_product_description)
    app.text_area("risk_description_input").set_value(test_risk_description)

    app.button("generate_questions_button").click()
    app.run()

    mock_openai.assert_called_once_with(api_key=test_api_key, base_url=DEFAULT_PROXY_BASE_URL)
    assert len(created_clients) == 1
    created_clients[0].chat.completions.create.assert_called_once_with(
        model=test_model_info.model_id,
        messages=[
            {
                "role": "user",
                "content": get_systematization_questions_prompt(test_product_description, test_risk_description),
            }
        ],
    )

    for i in range(len(test_questions)):
        assert app.text_area(f"answer_input_{i + 1}").label == rf"{i + 1}\. {test_questions[i]}"


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_error_when_answers_are_empty(mock_openai: Mock) -> None:
    test_questions = ["test question 1", "test question 2"]
    test_api_key = "test api key"
    test_risk_description = "test risk description"
    test_product_description = "test product description"
    test_model_info = ModelInfo.OPENAI_GPT_4O
    mock_openai.side_effect = make_openai_side_effect(test_api_key, test_questions)

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.model_info = test_model_info
    app.session_state.api_key = test_api_key
    app.session_state.risk_description = test_risk_description
    app.session_state.product_description = test_product_description

    app.run()

    app.text_area("answer_input_2").set_value("test answer to question 2")
    app.button("submit_answers_button").click()
    app.run()

    assert app.error[0].value == "Please answer question 1."


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_saves_answers_on_success(mock_openai: Mock) -> None:
    test_api_key = "test api key"
    test_model_info = ModelInfo.OPENAI_GPT_4O
    test_risk_description = "test risk description"
    test_product_description = "test product description"
    test_questions = ["test question 1", "test question 2"]
    test_answers = ["test answer to question 1", "test answer to question 2"]

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.model_info = test_model_info
    app.session_state.api_key = test_api_key
    app.session_state.risk_description = test_risk_description
    app.session_state.product_description = test_product_description
    app.session_state.follow_up_questions = test_questions

    app.run()

    app.text_area("answer_input_1").set_value(test_answers[0])
    app.text_area("answer_input_2").set_value(test_answers[1])

    mock_openai.side_effect = make_openai_side_effect(test_api_key, test_answers)

    app.button("submit_answers_button").click()
    app.run()

    assert app.session_state.systematization_answers == test_answers


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_results_when_answers_are_set(mock_openai: Mock) -> None:
    test_product_description = "test product description"
    test_risk_description = "test risk description"
    test_api_key = "test api key"
    test_model_info = ModelInfo.OPENAI_GPT_4O

    test_questions = ["test question 1", "test question 2"]
    test_answers = ["test answer to question 1", "test answer to question 2"]
    test_systematized_concepts = [
        {
            "title": "test concept 1",
            "body": "test body 1",
            "prompt_template": "test prompt template 1",
        },
        {
            "title": "test concept 2",
            "body": "test body 2",
            "prompt_template": "test prompt template 2",
        },
    ]

    created_clients: list[Mock] = []

    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        """
        Creates a mock OpenAI client configured with the expected credentials and a serialized concept response.
        
        Parameters:
            *args (Any): Positional arguments accepted by the mocked client factory.
            **kwargs (Any): Keyword arguments containing the API key and proxy URL.
        
        Returns:
            Mock: A context-manager-compatible mock client with a configured chat completion response.
        """
        assert kwargs.get("api_key") == test_api_key
        assert kwargs.get("base_url") == DEFAULT_PROXY_BASE_URL
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps(test_systematized_concepts)))]
        )
        created_clients.append(mock_client)
        return mock_client

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.model_info = test_model_info
    app.session_state.api_key = test_api_key
    app.session_state.risk_description = test_risk_description
    app.session_state.product_description = test_product_description
    app.session_state.follow_up_questions = test_questions

    app.run()

    app.text_area("answer_input_1").set_value(test_answers[0])
    app.text_area("answer_input_2").set_value(test_answers[1])

    mock_openai.side_effect = side_effect

    app.button("submit_answers_button").click()
    app.run()

    assert test_systematized_concepts[0]["title"] in app.markdown[4].value
    assert app.markdown[5].value == test_systematized_concepts[0]["body"]
    assert app.code[0].value == test_systematized_concepts[0]["prompt_template"]
    assert test_systematized_concepts[1]["title"] in app.markdown[8].value
    assert app.markdown[9].value == test_systematized_concepts[1]["body"]
    assert app.code[1].value == test_systematized_concepts[1]["prompt_template"]

    assert mock_openai.call_count == 1
    mock_openai.assert_called_with(api_key=test_api_key, base_url=DEFAULT_PROXY_BASE_URL)
    assert len(created_clients) == 1
    created_clients[0].chat.completions.create.assert_called_once_with(
        model=test_model_info.model_id,
        messages=[
            {
                "role": "user",
                "content": get_systematized_concepts_prompt(
                    test_product_description,
                    test_risk_description,
                    test_questions,
                    test_answers,
                ),
            }
        ],
    )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_error_when_systematized_concepts_are_none(mock_openai: Mock) -> None:
    test_product_description = "test product description"
    test_risk_description = "test risk description"
    test_api_key = "test api key"
    test_model_info = ModelInfo.OPENAI_GPT_4O

    test_questions = ["test question 1", "test question 2"]
    test_answers = ["test answer to question 1", "test answer to question 2"]

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.model_info = test_model_info
    app.session_state.api_key = test_api_key
    app.session_state.risk_description = test_risk_description
    app.session_state.product_description = test_product_description
    app.session_state.follow_up_questions = test_questions

    app.run()

    app.text_area("answer_input_1").set_value(test_answers[0])
    app.text_area("answer_input_2").set_value(test_answers[1])

    mock_openai.side_effect = make_openai_side_effect(test_api_key, None)

    app.button("submit_answers_button").click()
    app.run()

    mock_openai.assert_called_once_with(api_key=test_api_key, base_url=DEFAULT_PROXY_BASE_URL)

    assert app.error[0].value == "Error generating systematized concepts. Please try again."


@patch("aspis.ui.main.st.file_uploader")  # this has to be mocked because AppTest doesn't support file uploaders yet
def test_main_upload_file_success(mock_file_uploader: Mock) -> None:
    test_systematized_concepts = [
        SystematizedConcept(
            title="test concept 1",
            body="test body 1",
            prompt_template="test prompt template 1",
        ),
        SystematizedConcept(
            title="test concept 2",
            body="test body 2",
            prompt_template="test prompt template 2",
        ),
    ]
    test_yaml_data = {
        "product_description": "test product description",
        "risk_description": "test risk description",
        "follow_up_questions": ["test question 1", "test question 2"],
        "systematization_answers": ["test answer to question 1", "test answer to question 2"],
        "systematized_concepts": [asdict(concept) for concept in test_systematized_concepts],
    }

    mock_file_uploader.return_value = BytesIO(yaml.safe_dump(test_yaml_data).encode("utf-8"))

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    assert app.session_state.product_description == test_yaml_data["product_description"]
    assert app.session_state.risk_description == test_yaml_data["risk_description"]
    assert app.session_state.follow_up_questions == test_yaml_data["follow_up_questions"]
    assert app.session_state.systematization_answers == test_yaml_data["systematization_answers"]
    assert app.session_state.systematized_concepts == test_systematized_concepts


@patch("aspis.ui.main.st.file_uploader")  # this has to be mocked because AppTest doesn't support file uploaders yet
def test_main_upload_file_failure_missing_field(mock_file_uploader: Mock) -> None:
    test_systematized_concepts = [
        SystematizedConcept(
            title="test concept 1",
            body="test body 1",
            prompt_template="test prompt template 1",
        ),
        SystematizedConcept(
            title="test concept 2",
            body="test body 2",
            prompt_template="test prompt template 2",
        ),
    ]
    test_yaml_data = {
        "product_description": "test product description",
        "risk_description": "test risk description",
        "follow_up_questions": ["test question 1", "test question 2"],
        "systematization_answers": ["test answer to question 1", "test answer to question 2"],
        "systematized_concepts": [asdict(concept) for concept in test_systematized_concepts],
    }

    for key in test_yaml_data:
        test_yaml_data_copy = deepcopy(test_yaml_data)
        del test_yaml_data_copy[key]

        mock_file_uploader.return_value = BytesIO(yaml.safe_dump(test_yaml_data_copy).encode("utf-8"))

        app = AppTest.from_file("src/aspis/ui/main.py")
        app.run()

        assert app.error[0].value == f"Error loading saved results: Key '{key}' is missing from the saved results."

        mock_file_uploader.reset_mock()

    concept_keys = list(test_yaml_data["systematized_concepts"][0].keys())
    for key in concept_keys:
        test_yaml_data_copy = deepcopy(test_yaml_data)
        del test_yaml_data_copy["systematized_concepts"][0][key]

        mock_file_uploader.return_value = BytesIO(yaml.safe_dump(test_yaml_data_copy).encode("utf-8"))

        app = AppTest.from_file("src/aspis/ui/main.py")
        app.run()

        assert (
            app.error[0].value
            == f"Error loading saved results: Key '{key}' is missing from a systematized concept in the saved results."
        )

        mock_file_uploader.reset_mock()


@patch("aspis.ui.main.st.file_uploader")  # this has to be mocked because AppTest doesn't support file uploaders yet
def test_main_upload_file_failure_bad_format(mock_file_uploader: Mock) -> None:
    mock_file_uploader.return_value = BytesIO("[key: value".encode("utf-8"))

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    assert "Error loading saved results" in app.error[0].value


@patch("aspis.ui.main.st.download_button")  # this has to be mocked because AppTest doesn't support download buttons yet
def test_main_download_button(mock_download_button: Mock) -> None:
    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.api_key = "test api key"
    app.session_state.model_info = ModelInfo.OPENAI_GPT_4O
    app.session_state.product_description = "test product description"
    app.session_state.risk_description = "test risk description"
    app.session_state.follow_up_questions = ["test question 1", "test question 2"]
    app.session_state.systematization_answers = ["test answer to question 1", "test answer to question 2"]
    app.session_state.systematized_concepts = [
        SystematizedConcept(
            title="test concept 1",
            body="test body 1",
            prompt_template="test prompt template 1",
        ),
        SystematizedConcept(
            title="test concept 2",
            body="test body 2",
            prompt_template="test prompt template 2",
        ),
    ]
    app.run()

    mock_download_button.assert_called_with(
        label="⬇️ Download results",
        data=ANY,
        file_name="systematized_concepts.yaml",
        mime="text/yaml",
    )

    expected_yaml_data = {
        "product_description": app.session_state.product_description,
        "risk_description": app.session_state.risk_description,
        "follow_up_questions": app.session_state.follow_up_questions,
        "systematization_answers": app.session_state.systematization_answers,
        "systematized_concepts": [asdict(concept) for concept in app.session_state.systematized_concepts],
    }
    assert expected_yaml_data == yaml.safe_load(mock_download_button.call_args_list[0].kwargs["data"])
