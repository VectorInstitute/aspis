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

from aspis.inferencer import DEFAULT_OPENAI_TIMEOUT_SECONDS, ModelInfo, resolve_model_and_provider_url
from aspis.systematization import (
    SystematizedConcept,
    get_systematization_questions_prompt,
    get_systematized_concepts_prompt,
)
from aspis.ui.main import _apply_landing_form_submission


def make_openai_side_effect(api_key: str, return_value: Any) -> Callable[..., Mock]:
    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        assert kwargs.get("api_key") == api_key
        assert kwargs.get("base_url") == ModelInfo.OPENAI_GPT_4O.provider_url
        assert kwargs.get("timeout") == DEFAULT_OPENAI_TIMEOUT_SECONDS

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

    assert len(app.exception) == 0
    assert app.title[0].value == "🛡️ Aspis"
    assert "api_key" not in app.session_state
    assert "model_id" not in app.session_state
    assert "risk_description" not in app.session_state
    assert "product_description" not in app.session_state

    mock_openai.assert_not_called()
    assert app.selectbox("model_info_input").label == "Select the model you want to use:"
    assert app.selectbox("model_info_input").options == [model.friendly_name for model in list(ModelInfo)]
    assert app.selectbox("model_info_input").index == 0
    assert app.text_input("api_key_input").label == "Enter your API key:"
    assert app.text_input("proxy_base_url_input").label == "Proxy address"
    assert app.text_input("proxy_base_url_input").value == ""
    assert app.text_input("proxy_base_url_input").placeholder == "Type your proxy address"
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
    test_model = ModelInfo.OPENAI_GPT_4O
    test_risk_description = "test risk description"
    test_product_description = "test product description"

    created_clients: list[Mock] = []

    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        assert kwargs.get("api_key") == test_api_key
        assert kwargs.get("base_url") == ModelInfo.OPENAI_GPT_4O.provider_url
        assert kwargs.get("timeout") == DEFAULT_OPENAI_TIMEOUT_SECONDS
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
    app.session_state.model_id = test_model.model_id
    app.session_state.provider_url = test_model.provider_url
    app.session_state.risk_description = test_risk_description
    app.session_state.product_description = test_product_description

    app.run()

    assert len(app.exception) == 0
    assert mock_openai.call_count == 1
    mock_openai.assert_called_once_with(
        api_key=test_api_key,
        base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
    assert len(created_clients) == 1
    created_clients[0].chat.completions.create.assert_called_once_with(
        model=test_model.model_id,
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
    test_model = ModelInfo.OPENAI_GPT_4O
    mock_openai.side_effect = make_openai_side_effect(test_api_key, ["test question"])

    # Empty API key
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()
    app.selectbox("model_info_input").set_value(test_model)
    app.text_input("api_key_input").set_value("")
    app.text_area("product_description_input").set_value(test_product_description)
    app.text_area("risk_description_input").set_value(test_risk_description)

    app.button("generate_questions_button").click()
    app.run()

    assert app.error[0].value == "Please enter an API key before proceeding."

    # Empty risk description
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()
    app.selectbox("model_info_input").set_value(test_model)
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
    app.selectbox("model_info_input").set_value(test_model)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("risk_description_input").set_value(test_risk_description)
    app.text_area("product_description_input").set_value(test_product_description)

    app.run()

    app.button("generate_questions_button").click()
    app.run()

    assert len(app.exception) == 0
    assert len(app.error) == 0
    assert app.session_state.api_key == test_api_key
    assert app.session_state.model_id == test_model.model_id
    assert app.session_state.risk_description == test_risk_description
    assert app.session_state.product_description == test_product_description
    mock_openai.assert_called_once_with(
        api_key=test_api_key,
        base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_error_when_questions_are_none(mock_openai: Mock) -> None:
    test_api_key = "test api key"
    test_risk_description = "test risk description"
    test_product_description = "test product description"
    test_model = ModelInfo.OPENAI_GPT_4O
    mock_openai.side_effect = make_openai_side_effect(test_api_key, None)

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    app.selectbox("model_info_input").set_value(test_model)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("risk_description_input").set_value(test_risk_description)
    app.text_area("product_description_input").set_value(test_product_description)

    app.button("generate_questions_button").click()
    app.run()

    assert mock_openai.call_count == 1
    mock_openai.assert_called_once_with(
        api_key=test_api_key,
        base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
    assert app.error[0].value == "Error generating questions. Please try again."


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_questions_on_success(mock_openai: Mock) -> None:
    test_questions = ["test question 1", "test question 2"]
    test_api_key = "test api key"
    test_model = ModelInfo.OPENAI_GPT_4O
    test_product_description = "test product description"
    test_risk_description = "test risk description"

    created_clients: list[Mock] = []

    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        assert kwargs.get("api_key") == test_api_key
        assert kwargs.get("base_url") == ModelInfo.OPENAI_GPT_4O.provider_url
        assert kwargs.get("timeout") == DEFAULT_OPENAI_TIMEOUT_SECONDS
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

    app.selectbox("model_info_input").set_value(test_model)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("product_description_input").set_value(test_product_description)
    app.text_area("risk_description_input").set_value(test_risk_description)

    app.button("generate_questions_button").click()
    app.run()

    assert len(app.exception) == 0
    mock_openai.assert_called_once_with(
        api_key=test_api_key,
        base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
    assert len(created_clients) == 1
    created_clients[0].chat.completions.create.assert_called_once_with(
        model=test_model.model_id,
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
    test_model = ModelInfo.OPENAI_GPT_4O
    mock_openai.side_effect = make_openai_side_effect(test_api_key, test_questions)

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.model_id = test_model.model_id
    app.session_state.provider_url = test_model.provider_url
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
    test_model = ModelInfo.OPENAI_GPT_4O
    test_risk_description = "test risk description"
    test_product_description = "test product description"
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

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.model_id = test_model.model_id
    app.session_state.provider_url = test_model.provider_url
    app.session_state.api_key = test_api_key
    app.session_state.risk_description = test_risk_description
    app.session_state.product_description = test_product_description
    app.session_state.follow_up_questions = test_questions

    app.run()

    app.text_area("answer_input_1").set_value(test_answers[0])
    app.text_area("answer_input_2").set_value(test_answers[1])

    mock_openai.side_effect = make_openai_side_effect(test_api_key, test_systematized_concepts)

    app.button("submit_answers_button").click()
    app.run()

    assert len(app.exception) == 0
    assert app.session_state.systematization_answers == test_answers


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_render_results_when_answers_are_set(mock_openai: Mock) -> None:
    test_product_description = "test product description"
    test_risk_description = "test risk description"
    test_api_key = "test api key"
    test_model = ModelInfo.OPENAI_GPT_4O

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
        assert kwargs.get("api_key") == test_api_key
        assert kwargs.get("base_url") == ModelInfo.OPENAI_GPT_4O.provider_url
        assert kwargs.get("timeout") == DEFAULT_OPENAI_TIMEOUT_SECONDS
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps(test_systematized_concepts)))]
        )
        created_clients.append(mock_client)
        return mock_client

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.model_id = test_model.model_id
    app.session_state.provider_url = test_model.provider_url
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

    assert len(app.exception) == 0
    assert test_systematized_concepts[0]["title"] in app.markdown[4].value
    assert app.markdown[5].value == test_systematized_concepts[0]["body"]
    assert app.code[0].value == test_systematized_concepts[0]["prompt_template"]
    assert test_systematized_concepts[1]["title"] in app.markdown[8].value
    assert app.markdown[9].value == test_systematized_concepts[1]["body"]
    assert app.code[1].value == test_systematized_concepts[1]["prompt_template"]

    assert mock_openai.call_count == 1
    mock_openai.assert_called_with(
        api_key=test_api_key,
        base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )
    assert len(created_clients) == 1
    created_clients[0].chat.completions.create.assert_called_once_with(
        model=test_model.model_id,
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
    test_model = ModelInfo.OPENAI_GPT_4O

    test_questions = ["test question 1", "test question 2"]
    test_answers = ["test answer to question 1", "test answer to question 2"]

    app = AppTest.from_file("src/aspis/ui/main.py")

    app.session_state.model_id = test_model.model_id
    app.session_state.provider_url = test_model.provider_url
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

    mock_openai.assert_called_once_with(
        api_key=test_api_key,
        base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )

    assert app.error[0].value == "Error generating systematized concepts. Please try again."


@patch("aspis.ui.main.st.download_button")  # this has to be mocked because AppTest doesn't support download buttons yet
@patch("aspis.ui.main.st.file_uploader")  # this has to be mocked because AppTest doesn't support file uploaders yet
def test_main_upload_file_success(mock_file_uploader: Mock, mock_download_button: Mock) -> None:
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

    assert len(app.exception) == 0
    assert app.session_state.product_description == test_yaml_data["product_description"]
    assert app.session_state.risk_description == test_yaml_data["risk_description"]
    assert app.session_state.model_id == ModelInfo.OPENAI_GPT_4O.model_id
    assert app.session_state.follow_up_questions == test_yaml_data["follow_up_questions"]
    assert app.session_state.systematization_answers == test_yaml_data["systematization_answers"]
    assert app.session_state.systematized_concepts == test_systematized_concepts
    assert "Systematized Concepts" in app.markdown[1].value
    mock_download_button.assert_called_with(
        label="⬇️ Download results",
        data=ANY,
        file_name="systematized_concepts.yaml",
        mime="text/yaml",
    )
    downloaded = yaml.safe_load(mock_download_button.call_args_list[0].kwargs["data"])
    assert downloaded["model_id"] == ModelInfo.OPENAI_GPT_4O.model_id
    assert "proxy_base_url" not in downloaded
    assert "proxy" not in downloaded


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
    app.session_state.model_id = ModelInfo.OPENAI_GPT_4O.model_id
    app.session_state.provider_url = ModelInfo.OPENAI_GPT_4O.provider_url
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

    assert len(app.exception) == 0
    mock_download_button.assert_called_with(
        label="⬇️ Download results",
        data=ANY,
        file_name="systematized_concepts.yaml",
        mime="text/yaml",
    )

    expected_yaml_data = {
        "product_description": app.session_state.product_description,
        "risk_description": app.session_state.risk_description,
        "model_id": ModelInfo.OPENAI_GPT_4O.model_id,
        "follow_up_questions": app.session_state.follow_up_questions,
        "systematization_answers": app.session_state.systematization_answers,
        "systematized_concepts": [asdict(concept) for concept in app.session_state.systematized_concepts],
    }
    assert expected_yaml_data == yaml.safe_load(mock_download_button.call_args_list[0].kwargs["data"])


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_invalid_proxy_url_rejected(mock_openai: Mock) -> None:
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    app.selectbox("model_info_input").set_value(ModelInfo.OPENAI_GPT_4O)
    app.text_input("proxy_base_url_input").set_value("not-a-url")
    app.text_input("api_key_input").set_value("test api key")
    app.text_area("product_description_input").set_value("test product description")
    app.text_area("risk_description_input").set_value("test risk description")

    app.button("generate_questions_button").click()
    app.run()

    assert app.error[0].value == "Please enter a valid proxy address URL (http or https)."
    mock_openai.assert_not_called()


def assert_landing_page_rendered_without_inputs(app: AppTest) -> None:
    """Assert the landing form is still rendered and no landing input was persisted."""
    assert "product_description" not in app.session_state
    assert "risk_description" not in app.session_state
    assert "api_key" not in app.session_state
    assert app.text_area("product_description_input").label == "What is the description of your AI-powered product?"
    assert (
        app.text_area("risk_description_input").label
        == "What is the AI risk you want to create a measurement instrument for?"
    )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_failed_proxy_validation_does_not_persist_inputs(mock_openai: Mock) -> None:
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    app.selectbox("model_info_input").set_value(ModelInfo.OPENAI_GPT_4O)
    app.text_input("proxy_base_url_input").set_value("not-a-url")
    app.text_input("api_key_input").set_value("test api key")
    app.text_area("product_description_input").set_value("test product description")
    app.text_area("risk_description_input").set_value("test risk description")

    app.button("generate_questions_button").click()
    app.run()

    assert app.error[0].value == "Please enter a valid proxy address URL (http or https)."
    assert "model_id" not in app.session_state
    assert "provider_url" not in app.session_state
    assert_landing_page_rendered_without_inputs(app)
    mock_openai.assert_not_called()

    # A subsequent rerun (any widget interaction) must not bypass the landing page.
    app.run()

    assert_landing_page_rendered_without_inputs(app)
    mock_openai.assert_not_called()


class FakeSessionState(dict):  # type: ignore[type-arg]
    """Minimal stand-in for ``st.session_state`` supporting attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def submit_landing_form(
    selected_model: ModelInfo | str | None,
    proxy_input: str,
    product_description: str = "test product description",
    risk_description: str = "test risk description",
    api_key: str | None = "test api key",
) -> tuple[bool, FakeSessionState, list[str]]:
    """Call the landing-form handler with a fake session, collecting errors."""
    session_state = FakeSessionState()
    errors: list[str] = []

    with patch("aspis.ui.main.st") as mock_st:
        mock_st.session_state = session_state
        mock_st.error.side_effect = errors.append
        accepted = _apply_landing_form_submission(
            product_description, risk_description, api_key, selected_model, proxy_input
        )

    return accepted, session_state, errors


def assert_nothing_persisted(session_state: FakeSessionState) -> None:
    """Assert a rejected submission left no landing-page value in session state."""
    for key in ("product_description", "risk_description", "api_key", "model_id", "provider_url"):
        assert key not in session_state


def test_apply_landing_form_submission_custom_model_without_proxy_rejected() -> None:
    accepted, session_state, errors = submit_landing_form("my-custom-model", "")

    assert accepted is False
    assert errors == ["Please enter a proxy address for custom model IDs."]
    assert_nothing_persisted(session_state)


def test_apply_landing_form_submission_custom_model_with_invalid_proxy_rejected() -> None:
    accepted, session_state, errors = submit_landing_form("my-custom-model", "not-a-url")

    assert accepted is False
    assert errors == ["Please enter a valid proxy address URL (http or https)."]
    assert_nothing_persisted(session_state)


def test_apply_landing_form_submission_known_model_with_invalid_proxy_rejected() -> None:
    accepted, session_state, errors = submit_landing_form(ModelInfo.OPENAI_GPT_4O, "not-a-url")

    assert accepted is False
    assert errors == ["Please enter a valid proxy address URL (http or https)."]
    assert_nothing_persisted(session_state)


def test_apply_landing_form_submission_known_model_without_proxy_accepted() -> None:
    accepted, session_state, errors = submit_landing_form(ModelInfo.OPENAI_GPT_4O, "")

    assert accepted is True
    assert errors == []
    assert session_state["model_id"] == ModelInfo.OPENAI_GPT_4O.model_id
    assert session_state["provider_url"] == ModelInfo.OPENAI_GPT_4O.provider_url


def test_apply_landing_form_submission_known_model_with_valid_proxy_accepted() -> None:
    accepted, session_state, errors = submit_landing_form(ModelInfo.OPENAI_GPT_4O, "https://1.1.1.1/v1")

    assert accepted is True
    assert errors == []
    assert session_state["model_id"] == ModelInfo.OPENAI_GPT_4O.model_id
    assert session_state["provider_url"] == "https://1.1.1.1/v1"


def test_apply_landing_form_submission_custom_model_with_valid_proxy_accepted() -> None:
    accepted, session_state, errors = submit_landing_form("my-custom-model", "https://1.1.1.1/v1")

    assert accepted is True
    assert errors == []
    assert session_state["model_id"] == "my-custom-model"
    assert session_state["provider_url"] == "https://1.1.1.1/v1"
    assert session_state["product_description"] == "test product description"
    assert session_state["risk_description"] == "test risk description"
    assert session_state["api_key"] == "test api key"


@pytest.mark.parametrize(
    ("product_description", "risk_description", "api_key", "expected_error"),
    [
        ("", "test risk description", "test api key", "Please enter a product description before proceeding."),
        ("test product description", "", "test api key", "Please enter a risk description before proceeding."),
        ("test product description", "test risk description", "", "Please enter an API key before proceeding."),
    ],
)
def test_apply_landing_form_submission_missing_inputs_persist_nothing(
    product_description: str,
    risk_description: str,
    api_key: str,
    expected_error: str,
) -> None:
    accepted, session_state, errors = submit_landing_form(
        ModelInfo.OPENAI_GPT_4O,
        "",
        product_description=product_description,
        risk_description=risk_description,
        api_key=api_key,
    )

    assert accepted is False
    assert errors == [expected_error]
    assert_nothing_persisted(session_state)


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_known_model_with_empty_proxy_uses_provider_default(mock_openai: Mock) -> None:
    test_api_key = "test api key"
    mock_openai.side_effect = make_openai_side_effect(test_api_key, ["test question"])

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    app.selectbox("model_info_input").set_value(ModelInfo.OPENAI_GPT_4O)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("product_description_input").set_value("test product description")
    app.text_area("risk_description_input").set_value("test risk description")

    app.button("generate_questions_button").click()
    app.run()

    assert len(app.exception) == 0
    assert len(app.error) == 0
    assert app.session_state.provider_url == ModelInfo.OPENAI_GPT_4O.provider_url
    assert app.session_state.model_id == ModelInfo.OPENAI_GPT_4O.model_id
    mock_openai.assert_called_once_with(
        api_key=test_api_key,
        base_url=ModelInfo.OPENAI_GPT_4O.provider_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


@pytest.mark.integration_test
@patch("aspis.inferencer.OpenAI")
def test_main_known_model_with_custom_proxy(mock_openai: Mock) -> None:
    test_api_key = "test api key"
    test_proxy = "https://1.1.1.1/v1"

    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        assert kwargs.get("base_url") == test_proxy
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps(["test question"])))]
        )
        return mock_client

    mock_openai.side_effect = side_effect

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    app.selectbox("model_info_input").set_value(ModelInfo.OPENAI_GPT_4O)
    app.text_input("proxy_base_url_input").set_value(test_proxy)
    app.text_input("api_key_input").set_value(test_api_key)
    app.text_area("product_description_input").set_value("test product description")
    app.text_area("risk_description_input").set_value("test risk description")

    app.button("generate_questions_button").click()
    app.run()

    assert len(app.exception) == 0
    assert len(app.error) == 0
    assert app.session_state.provider_url == test_proxy
    mock_openai.assert_called_once_with(
        api_key=test_api_key,
        base_url=test_proxy,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


def test_landing_page_inputs_are_inside_the_form() -> None:
    """A browser only flushes pending edits of widgets that live inside the form."""
    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    assert len(app.exception) == 0
    form_id = app.button("generate_questions_button").form_id
    assert form_id != ""
    assert app.selectbox("model_info_input").form_id == form_id
    # AppTest cannot type a custom option, so assert the model selectbox still allows
    # one now that it lives inside the form.
    assert app.selectbox("model_info_input").proto.accept_new_options is True
    assert app.text_input("api_key_input").form_id == form_id
    assert app.text_input("proxy_base_url_input").form_id == form_id
    assert app.text_area("product_description_input").form_id == form_id
    assert app.text_area("risk_description_input").form_id == form_id


def test_resolve_model_and_provider_url_known_model_defaults_from_ui() -> None:
    model_id, provider_url = resolve_model_and_provider_url(ModelInfo.OPENAI_GPT_4O.model_id, "")
    assert model_id == ModelInfo.OPENAI_GPT_4O.model_id
    assert provider_url == ModelInfo.OPENAI_GPT_4O.provider_url


def test_resolve_model_and_provider_url_known_model_id_string_defaults_from_ui() -> None:
    model_id, provider_url = resolve_model_and_provider_url(ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW.model_id, "")
    assert model_id == ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW.model_id
    assert provider_url == ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW.provider_url


def test_resolve_model_and_provider_url_known_model_override_from_ui() -> None:
    model_id, provider_url = resolve_model_and_provider_url(ModelInfo.OPENAI_GPT_4O.model_id, "https://1.1.1.1/v1")
    assert model_id == ModelInfo.OPENAI_GPT_4O.model_id
    assert provider_url == "https://1.1.1.1/v1"


def test_resolve_model_and_provider_url_custom_model_requires_proxy_from_ui() -> None:
    with pytest.raises(ValueError, match="Please enter a proxy address for custom model IDs"):
        resolve_model_and_provider_url("my-custom-model", "")


def test_resolve_model_and_provider_url_custom_model_with_proxy_from_ui() -> None:
    model_id, provider_url = resolve_model_and_provider_url("my-custom-model", "https://1.1.1.1/v1")
    assert model_id == "my-custom-model"
    assert provider_url == "https://1.1.1.1/v1"


def test_resolve_model_and_provider_url_rejects_invalid_url_from_ui() -> None:
    with pytest.raises(ValueError, match="Please enter a valid proxy address URL"):
        resolve_model_and_provider_url(ModelInfo.OPENAI_GPT_4O.model_id, "not-a-url")


@patch("aspis.ui.main.st.download_button")
@patch("aspis.ui.main.st.file_uploader")
def test_main_upload_restores_optional_model_id(mock_file_uploader: Mock, mock_download_button: Mock) -> None:
    test_systematized_concepts = [
        SystematizedConcept(
            title="test concept 1",
            body="test body 1",
            prompt_template="test prompt template 1",
        ),
    ]
    test_yaml_data = {
        "product_description": "test product description",
        "risk_description": "test risk description",
        "model_id": ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW.model_id,
        "follow_up_questions": ["test question 1"],
        "systematization_answers": ["test answer 1"],
        "systematized_concepts": [asdict(concept) for concept in test_systematized_concepts],
    }

    mock_file_uploader.return_value = BytesIO(yaml.safe_dump(test_yaml_data).encode("utf-8"))

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    assert len(app.exception) == 0
    assert app.session_state.model_id == ModelInfo.GOOGLE_GEMINI_3_FLASH_PREVIEW.model_id
    assert app.session_state.systematized_concepts == test_systematized_concepts


@patch("aspis.ui.main.st.download_button")
@patch("aspis.ui.main.st.file_uploader")
def test_main_upload_restores_custom_model_id(mock_file_uploader: Mock, mock_download_button: Mock) -> None:
    test_systematized_concepts = [
        SystematizedConcept(
            title="test concept 1",
            body="test body 1",
            prompt_template="test prompt template 1",
        ),
    ]
    test_yaml_data = {
        "product_description": "test product description",
        "risk_description": "test risk description",
        "model_id": "my-custom-model",
        "follow_up_questions": ["test question 1"],
        "systematization_answers": ["test answer 1"],
        "systematized_concepts": [asdict(concept) for concept in test_systematized_concepts],
    }

    mock_file_uploader.return_value = BytesIO(yaml.safe_dump(test_yaml_data).encode("utf-8"))

    app = AppTest.from_file("src/aspis/ui/main.py")
    app.run()

    assert len(app.exception) == 0
    assert app.session_state.model_id == "my-custom-model"
    assert app.session_state.systematized_concepts == test_systematized_concepts
    mock_download_button.assert_called_with(
        label="⬇️ Download results",
        data=ANY,
        file_name="systematized_concepts.yaml",
        mime="text/yaml",
    )
    downloaded = yaml.safe_load(mock_download_button.call_args_list[0].kwargs["data"])
    assert downloaded["model_id"] == "my-custom-model"
    assert "proxy_base_url" not in downloaded
    assert "proxy" not in downloaded
