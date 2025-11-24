"""UI for the Aspis application."""

import streamlit as st

from aspis.sistematization import (
    SistematizedConcept,
    get_sistematization_questions,
    get_sistematized_concepts,
)


def main() -> None:
    """Entry point for the Aspis application."""
    st.set_page_config(page_title="Aspis", page_icon="🛡️", layout="centered")
    st.title("🛡️ Aspis")

    openai_api_key = st.session_state.get("openai_api_key", "")
    risk_description = st.session_state.get("risk_description", "")
    product_description = st.session_state.get("product_description", "")
    sistematization_answers = st.session_state.get("sistematization_answers", None)
    follow_up_questions = st.session_state.get("follow_up_questions", None)

    if not openai_api_key or not product_description or not risk_description:
        render_landing_page()

    elif sistematization_answers is not None and follow_up_questions is not None:
        # Answers have been submitted, generate and display systematized concepts
        with st.spinner("Generating systematized concepts..."):
            sistematized_concepts = get_sistematized_concepts(
                product_description=product_description,
                risk_description=risk_description,
                questions=follow_up_questions,
                answers=sistematization_answers,
                openai_api_key=openai_api_key,
            )

        if sistematized_concepts is None:
            st.error("Error generating systematized concepts. Please try again.")
            return

        render_sistematized_concepts(sistematized_concepts)

    else:
        # Generate questions if not already generated
        if follow_up_questions is None or len(follow_up_questions) == 0:
            with st.spinner("Generating questions..."):
                follow_up_questions = get_sistematization_questions(
                    openai_api_key=openai_api_key,
                    risk_description=risk_description,
                    product_description=product_description,
                )

            if follow_up_questions is None or len(follow_up_questions) == 0:
                st.error("Error generating questions. Please try again.")
                return

        st.session_state.follow_up_questions = follow_up_questions

        render_follow_up_questions(follow_up_questions)


def render_landing_page() -> None:
    """Render the landing page elements."""
    st.markdown("Welcome to Aspis!")

    with st.form("input_form"):
        # Product description text area
        current_product_description = st.text_area(
            label="What is the description of your AI-powered product?",
            placeholder="Enter your product description here...",
            help=(
                "Your product description is used to generate a measurement instrument for an AI risk. "
                "Please describe your product in a comprehensive way."
            ),
        )

        # Risk description text area
        current_risk_description = st.text_area(
            label="What is the AI risk you want to create a measurement instrument for?",
            placeholder="Enter your risk description here...",
            help=(
                "Your risk description is used to generate a risk assessment. Please describe the "
                "AI risk your product is exposed to in order to generate a measurement instrument."
            ),
        )

        # API key text input
        current_openai_api_key = st.text_input(
            label="Enter your Open AI API key:",
            placeholder="Paste your API key here...",
            help="Your API key is used to authenticate your requests to the Open AI API.",
            type="password",
        )

        if st.form_submit_button("Generate Questions", type="primary"):
            if current_product_description.strip():
                st.session_state.product_description = current_product_description
            else:
                st.error("Please enter a product description before proceeding.")
                return

            if current_risk_description.strip():
                st.session_state.risk_description = current_risk_description
            else:
                st.error("Please enter a risk description before proceeding.")
                return

            if current_openai_api_key.strip():
                st.session_state.openai_api_key = current_openai_api_key
            else:
                st.error("Please enter an Open AI API key before proceeding.")
                return

            # If it gets here, all the inputs are set, so rerun the UI
            st.rerun()


def render_follow_up_questions(follow_up_questions: list[str]) -> None:
    """Render the follow up questions to be asked to the user.

    Args:
        follow_up_questions: The follow up questions.
    """
    st.markdown("### Follow Up Questions")

    with st.form("questions_form"):
        current_answers = [""] * len(follow_up_questions)
        for i in range(len(follow_up_questions)):
            current_answers[i] = st.text_area(
                label=rf"{i + 1}\. {follow_up_questions[i]}",
                placeholder="Enter your answer here...",
            )

        if st.form_submit_button("Submit Answers", type="primary"):
            for i in range(len(current_answers)):
                if not current_answers[i].strip():
                    st.error(f"Please answer question {i + 1}.")
                    return

            st.session_state.sistematization_answers = current_answers
            st.rerun()


def render_sistematized_concepts(sistematized_concepts: list[SistematizedConcept]) -> None:
    """Render the systematized concepts with titles and bodies.

    Args:
        sistematized_concepts: The list of systematized concepts to display.
    """
    st.markdown("### Systematized Concepts")

    st.markdown(
        "Based on your answers, the following systematized concepts have been generated. "
        "These represent specific formulations of the background concepts that can be "
        "operationalized into a measurement instrument."
    )

    for i, concept in enumerate(sistematized_concepts, 1):
        with st.container():
            st.markdown(f"#### {i}. {concept.title}")
            st.markdown(concept.body)

            with st.expander("📝 Measurement Prompt Template", expanded=False):
                st.markdown("**Use this prompt template with an LLM judge to measure this concept:**")
                st.code(concept.prompt_template, language="text")
                st.markdown("*Replace `<text_to_evaluate/>` with the text you want to evaluate.*")

            st.divider()


if __name__ == "__main__":
    main()
