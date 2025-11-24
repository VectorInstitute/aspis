"""Test for the main module."""

from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest


def test_main_render_inputs_when_empty() -> None:
    app = AppTest.from_file("src/aspis/main.py")
    app.run()

    assert app.title[0].value == "🛡️ Aspis"
    assert "openai_api_key" not in app.session_state
    assert "risk_description" not in app.session_state
    assert "product_description" not in app.session_state

    assert len(app.text_input) == 1
    assert app.text_input[0].label == "Enter your Open AI API key:"
    assert len(app.text_area) == 2
    assert app.text_area[0].label == "What is the description of your AI-powered product?"
    assert app.text_area[1].label == "What is the AI risk you want to create a measurement instrument for?"


@patch("aspis.sistematization.get_sistematization_questions")
def test_main_ask_for_questions_when_inputs_are_set(mock_get_sistematization_questions: Mock) -> None:
    app = AppTest.from_file("src/aspis/main.py")

    app.session_state.openai_api_key = "test api key"
    app.session_state.risk_description = "test risk description"
    app.session_state.product_description = "test product description"

    app.run()

    assert mock_get_sistematization_questions.call_count == 1
    call_args_list = mock_get_sistematization_questions.call_args_list
    assert call_args_list[0].kwargs["risk_description"] == "test risk description"
    assert call_args_list[0].kwargs["product_description"] == "test product description"
    assert call_args_list[0].kwargs["openai_api_key"] == "test api key"


@patch("aspis.sistematization.get_sistematization_questions")
def test_main_render_error_messages_when_inputs_are_not_set(mock_get_sistematization_questions: Mock) -> None:
    test_api_key = "test api key"
    test_risk_description = "test risk description"
    test_product_description = "test product description"
    mock_get_sistematization_questions.return_value = ["test question"]

    # Empty API key
    app = AppTest.from_file("src/aspis/main.py")
    app.run()
    app.text_input[0].set_value("")
    app.text_area[0].set_value(test_product_description)
    app.text_area[1].set_value(test_risk_description)

    app.button[0].click()
    app.run()

    assert app.error[0].value == "Please enter an Open AI API key before proceeding."

    # Empty risk description
    app = AppTest.from_file("src/aspis/main.py")
    app.run()
    app.text_input[0].set_value(test_api_key)
    app.text_area[1].set_value("")
    app.text_area[0].set_value(test_product_description)

    app.button[0].click()
    app.run()

    assert app.error[0].value == "Please enter a risk description before proceeding."

    # Empty product description
    app = AppTest.from_file("src/aspis/main.py")
    app.run()
    app.text_input[0].set_value(test_api_key)
    app.text_area[1].set_value(test_risk_description)
    app.text_area[0].set_value("")

    app.button[0].click()
    app.run()

    assert app.error[0].value == "Please enter a product description before proceeding."

    # All inputs are set
    app = AppTest.from_file("src/aspis/main.py")
    app.run()
    app.text_input[0].set_value(test_api_key)
    app.text_area[1].set_value(test_risk_description)
    app.text_area[0].set_value(test_product_description)

    app.run()

    app.button[0].click()
    app.run()

    assert len(app.error) == 0
    assert app.session_state.openai_api_key == test_api_key
    assert app.session_state.risk_description == test_risk_description
    assert app.session_state.product_description == test_product_description
    mock_get_sistematization_questions.assert_called()


@patch("aspis.sistematization.get_sistematization_questions")
def test_main_render_error_when_questions_are_none(mock_get_sistematization_questions: Mock) -> None:
    mock_get_sistematization_questions.return_value = None

    app = AppTest.from_file("src/aspis/main.py")
    app.run()

    app.text_input[0].set_value("test api key")
    app.text_area[1].set_value("test risk description")
    app.text_area[0].set_value("test product description")

    app.button[0].click()
    app.run()

    mock_get_sistematization_questions.assert_called_with(
        product_description="test product description",
        risk_description="test risk description",
        openai_api_key="test api key",
    )
    assert app.error[0].value == "Error generating questions. Please try again."


@patch("aspis.sistematization.get_sistematization_questions")
def test_main_render_questions_on_success(mock_get_sistematization_questions: Mock) -> None:
    test_questions = ["test question 0", "test question 1"]
    mock_get_sistematization_questions.return_value = test_questions

    app = AppTest.from_file("src/aspis/main.py")
    app.run()

    app.text_input[0].set_value("test api key")
    app.text_area[1].set_value("test risk description")
    app.text_area[0].set_value("test product description")

    app.button[0].click()
    app.run()

    mock_get_sistematization_questions.assert_called_with(
        product_description="test product description",
        risk_description="test risk description",
        openai_api_key="test api key",
    )
    for i in range(len(test_questions)):
        assert app.text_area[i].label == rf"{i + 1}\. {test_questions[i]}"


@patch("aspis.sistematization.get_sistematization_questions")
def test_main_error_when_answers_are_empty(mock_get_sistematization_questions: Mock) -> None:
    test_questions = ["test question 1", "test question 2"]
    mock_get_sistematization_questions.return_value = test_questions

    app = AppTest.from_file("src/aspis/main.py")
    app.run()

    app.text_input[0].set_value("test api key")
    app.text_area[1].set_value("test risk description")
    app.text_area[0].set_value("test product description")

    app.button[0].click()
    app.run()

    app.text_area[1].set_value("test answer to question 2")
    app.button[0].click()
    app.run()

    assert app.error[0].value == "Please answer question 1."


@patch("aspis.sistematization.get_sistematization_questions")
def test_main_saves_answers_on_success(mock_get_sistematization_questions: Mock) -> None:
    test_questions = ["test question 0", "test question 1"]
    test_answers = ["test answer to question 0", "test answer to question 1"]
    mock_get_sistematization_questions.return_value = test_questions

    app = AppTest.from_file("src/aspis/main.py")
    app.run()

    app.text_input[0].set_value("test api key")
    app.text_area[1].set_value("test risk description")
    app.text_area[0].set_value("test product description")

    app.button[0].click()
    app.run()

    app.text_area[0].set_value(test_answers[0])
    app.text_area[1].set_value(test_answers[1])
    app.button[0].click()
    app.run()

    assert app.session_state.sistematization_answers == test_answers
