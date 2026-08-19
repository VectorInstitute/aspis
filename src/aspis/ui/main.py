"""UI for the Aspis application."""

from dataclasses import asdict
from pathlib import Path
from typing import Any

import streamlit as st
import yaml
from streamlit_searchbox import st_searchbox

from aspis.providers import ModelInfo, resolve_model_and_provider_url
from aspis.risk_catalog import (
    RiskEntry,
    append_risk_text,
    format_dropdown_label,
    load_all_risks,
    search_risks,
)
from aspis.systematization import (
    SystematizedConcept,
    get_systematization_questions,
    get_systematized_concepts,
)


_RISK_SEARCH_KEY = "risk_search_input"
_PENDING_RISK_DESCRIPTION_KEY = "pending_risk_description"


def _apply_pending_risk_append(session_state: Any) -> None:
    """Apply a pending taxonomy append before risk widgets are instantiated.

    Streamlit forbids mutating a widget key after that widget is created in the
    same run, so searchbox selection stores the new text on a non-widget key and
    this runs first on the next rerun.
    """
    pending = session_state.pop(_PENDING_RISK_DESCRIPTION_KEY, None)
    if pending is None:
        return
    session_state["risk_description_input"] = pending
    session_state.pop(_RISK_SEARCH_KEY, None)


def _stash_selected_risk(entry: Any) -> None:
    """Queue an attributed catalog append for the next run.

    Args:
        entry: Selected catalog entry from the searchbox.
    """
    if not isinstance(entry, RiskEntry):
        return
    existing = st.session_state.get("risk_description_input", "") or ""
    st.session_state[_PENDING_RISK_DESCRIPTION_KEY] = append_risk_text(existing, entry)


def _search_risk_options(query: str) -> list[tuple[str, RiskEntry]]:
    """Return ranked searchbox options as ``(label, entry)`` pairs.

    Args:
        query: Live searchbox text.

    Returns:
        Labels for the dropdown and the catalog entries they select.
    """
    return [(format_dropdown_label(entry), entry) for entry in search_risks(query, load_all_risks())]


def _apply_landing_form_submission(
    product_description: str,
    risk_description: str,
    api_key: str | None,
    selected_model: ModelInfo | str | None,
    proxy_value: str,
) -> bool:
    """Validate landing-page inputs and store them in session state.

    All inputs are validated before anything is written, so a failed submission
    leaves session state untouched and keeps the user on the landing page.

    Args:
        product_description: The submitted product description.
        risk_description: The submitted risk description.
        api_key: The submitted API key.
        selected_model: The selectbox value (known ``ModelInfo`` or custom model ID).
        proxy_value: The submitted proxy address, empty when the user left it blank.

    Returns:
        True when validation succeeded and state was updated; False when an error
        was shown and the caller should stop.
    """
    if not product_description.strip():
        st.error("Please enter a product description before proceeding.")
        return False

    if not risk_description.strip():
        st.error("Please enter a risk description before proceeding.")
        return False

    if not api_key or not api_key.strip():
        st.error("Please enter an API key before proceeding.")
        return False

    if selected_model is None or (isinstance(selected_model, str) and not selected_model.strip()):
        st.error("Please select a model before proceeding.")
        return False

    model_id = selected_model.model_id if isinstance(selected_model, ModelInfo) else selected_model.strip()
    try:
        model_id, provider_url = resolve_model_and_provider_url(model_id, proxy_value)
    except ValueError as e:
        st.error(str(e))
        return False

    st.session_state.product_description = product_description
    st.session_state.risk_description = risk_description
    st.session_state.api_key = api_key
    st.session_state.model_id = model_id
    st.session_state.provider_url = provider_url
    return True


def main() -> None:
    """Entry point for the Aspis application."""
    # Headers
    st.set_page_config(page_title="Aspis", page_icon="🛡️", layout="centered")
    css_path = Path(__file__).parent.parent / "assets" / "styles.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
    st.title("🛡️ Aspis")

    # Session state
    api_key = st.session_state.get("api_key", "")
    model_id = st.session_state.get("model_id")
    provider_url = st.session_state.get("provider_url")
    risk_description = st.session_state.get("risk_description", "")
    product_description = st.session_state.get("product_description", "")
    follow_up_questions = st.session_state.get("follow_up_questions", None)
    systematization_answers = st.session_state.get("systematization_answers", None)
    systematized_concepts = st.session_state.get("systematized_concepts", None)

    # Rendering the landing page
    if not model_id or not api_key or not product_description or not risk_description:
        render_landing_page()
        render_upload_button()

    # Generating and rendering the follow up questions
    elif systematization_answers is None:
        # Generate questions if not already generated
        if follow_up_questions is None or len(follow_up_questions) == 0:
            if not provider_url or not api_key:
                st.error("Missing provider URL or API key. Please start over from the landing page.")
                return
            with st.spinner("Generating questions..."):
                follow_up_questions = get_systematization_questions(
                    product_description=product_description,
                    risk_description=risk_description,
                    api_key=api_key,
                    model_id=model_id,
                    provider_url=provider_url,
                )

        if follow_up_questions is None or len(follow_up_questions) == 0:
            st.error("Error generating questions. Please try again.")
            return

        st.session_state.follow_up_questions = follow_up_questions

        render_follow_up_questions(follow_up_questions)

    # Generating and rendering the systematized concepts
    else:
        if systematized_concepts is None:
            if not provider_url or not api_key:
                st.error("Missing provider URL or API key. Please start over from the landing page.")
                return
            # Answers have been submitted, generate and display systematized concepts
            with st.spinner("Generating systematized concepts..."):
                systematized_concepts = get_systematized_concepts(
                    product_description=product_description,
                    risk_description=risk_description,
                    questions=follow_up_questions,
                    answers=systematization_answers,
                    api_key=api_key,
                    model_id=model_id,
                    provider_url=provider_url,
                )

        if systematized_concepts is None:
            st.error("Error generating systematized concepts. Please try again.")
            return

        st.session_state.systematized_concepts = systematized_concepts

        render_systematized_concepts(systematized_concepts)


def render_landing_page() -> None:
    """Render the landing page elements."""
    st.markdown("##### Welcome to Aspis!")
    st.markdown(
        "To generate a measurement instrument for an AI risk, please start by answering the following questions:"
    )

    _apply_pending_risk_append(st.session_state)

    current_product_description = st.text_area(
        label="What is the description of your AI-powered product?",
        placeholder="Enter your product description here...",
        help=(
            "Your product description is used to generate a measurement instrument for an AI risk. "
            "Please describe your product in a comprehensive way."
        ),
        key="product_description_input",
    )

    st.markdown(
        '<p class="risk-field-title">What is the AI risk you want to create a measurement instrument for?</p>',
        unsafe_allow_html=True,
    )

    # Live typeahead needs reruns as the user types; the landing page is not an st.form.
    if not load_all_risks():
        st.warning("Risk taxonomy search is unavailable. You can still enter a custom risk description.")
    st_searchbox(
        _search_risk_options,
        placeholder='Search AI Risk library (Optional, e.g. type "bias", "privacy", "misinformation"...)',
        key=_RISK_SEARCH_KEY,
        clear_on_submit=True,
        submit_function=_stash_selected_risk,
    )

    current_risk_description = st.text_area(
        label="Risk description",
        label_visibility="collapsed",
        placeholder="Or enter your risk description here...",
        help=(
            "Your risk description is used to generate a risk assessment. Please describe the "
            "AI risk your product is exposed to in order to generate a measurement instrument. "
            "Selecting a library match above appends it here."
        ),
        key="risk_description_input",
    )

    st.markdown(
        '<p style="font-size: 0.875rem; margin-bottom: 0.25rem;">Select the model to use and enter its API key:</p>',
        unsafe_allow_html=True,
    )
    column_model, column_api_key = st.columns([0.3, 0.7])
    with column_model:
        model_options = list(ModelInfo)
        current_model_info = st.selectbox(
            label="Select the model you want to use:",
            label_visibility="collapsed",
            options=model_options,
            index=0,
            key="model_info_input",
            accept_new_options=True,
            help="Pick a known model or type a custom model ID. Custom model IDs require a proxy address.",
        )

    with column_api_key:
        current_api_key = st.text_input(
            label="Enter your API key:",
            label_visibility="collapsed",
            placeholder="Paste your API key here...",
            help="Your API key is used to authenticate your requests to the model API.",
            type="password",
            key="api_key_input",
        )

    with st.expander("Proxy details"):
        current_proxy = st.text_input(
            label="Proxy address",
            placeholder="Type your proxy address",
            help=(
                "OpenAI-compatible base URL. Leave blank for known models to use their "
                "provider default. Required for custom model IDs."
            ),
            key="proxy_base_url_input",
        )

    generate_clicked = st.button("Generate Questions", type="primary", key="generate_questions_button")
    if generate_clicked and _apply_landing_form_submission(
        current_product_description,
        current_risk_description,
        current_api_key,
        current_model_info,
        current_proxy,
    ):
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
                key=f"answer_input_{i + 1}",
            )

        if st.form_submit_button("Submit Answers", type="primary", key="submit_answers_button"):
            for i in range(len(current_answers)):
                if not current_answers[i].strip():
                    st.error(f"Please answer question {i + 1}.")
                    return

            st.session_state.systematization_answers = current_answers
            st.rerun()


def render_systematized_concepts(systematized_concepts: list[SystematizedConcept]) -> None:
    """Render the systematized concepts with titles and bodies.

    Args:
        systematized_concepts: The list of systematized concepts to display.
    """
    st.markdown("### Systematized Concepts")

    st.markdown(
        "Based on your answers, the following systematized concepts have been generated. "
        "These represent specific formulations of the background concepts that can be "
        "operationalized into a measurement instrument."
    )

    st.markdown("You can download the results in a YAML file for future use by clicking the button below.")

    render_download_button()

    for i, concept in enumerate(systematized_concepts, 1):
        with st.container():
            st.markdown(f"#### {i}. {concept.title}")
            st.markdown(concept.body)

            with st.expander("📝 Measurement Prompt Template", expanded=False):
                st.markdown("**Use this prompt template with an LLM judge to measure this concept:**")
                st.code(concept.prompt_template, language="text", wrap_lines=True)
                st.markdown("*Replace `<text_to_evaluate/>` with the text you want to evaluate.*")

            if i < len(systematized_concepts):
                st.divider()


def render_download_button() -> None:
    """Render the download button to save the results."""
    file_contents = {
        "product_description": st.session_state.product_description,
        "risk_description": st.session_state.risk_description,
        "model_id": st.session_state.model_id,
        "follow_up_questions": st.session_state.follow_up_questions,
        "systematization_answers": st.session_state.systematization_answers,
        "systematized_concepts": [asdict(concept) for concept in st.session_state.systematized_concepts],
    }
    yaml_data = yaml.safe_dump(file_contents, default_flow_style=False, allow_unicode=True, sort_keys=False)

    st.download_button(
        label="⬇️ Download results",
        data=yaml_data,
        file_name="systematized_concepts.yaml",
        mime="text/yaml",
    )


def render_upload_button() -> None:
    """Render the upload button to load saved results."""
    st.markdown("##### 🗂️ Upload previously saved results:")
    uploaded_file = st.file_uploader(
        label="*.yaml file",
        type=["yaml", "yml"],
        help="Upload a previously saved YAML file to restore your results.",
        key="upload_file_input",
    )

    if uploaded_file is None:
        return

    # Load and validate the file
    try:
        saved_results = yaml.safe_load(uploaded_file)

        required_keys = [
            "product_description",
            "risk_description",
            "follow_up_questions",
            "systematization_answers",
            "systematized_concepts",
        ]
        for key in required_keys:
            if key not in saved_results:
                raise ValueError(f"Key '{key}' is missing from the saved results.")

        systematized_concepts_required_keys = ["title", "body", "prompt_template"]
        for concept in saved_results["systematized_concepts"]:
            for key in systematized_concepts_required_keys:
                if key not in concept:
                    raise ValueError(f"Key '{key}' is missing from a systematized concept in the saved results.")

    except Exception as e:
        st.error(f"Error loading saved results: {e}")
        return

    st.session_state.product_description = saved_results["product_description"]
    st.session_state.risk_description = saved_results["risk_description"]
    # Note: API key is set to a placeholder because it can't be None,
    # we're restoring saved results and don't need to make new API calls at this stage
    st.session_state.api_key = "placeholder-key"
    saved_model_id = saved_results.get("model_id")
    st.session_state.model_id = str(saved_model_id) if saved_model_id else ModelInfo.OPENAI_GPT_4O.model_id
    # Do not invent provider_url on upload — results path does not need it; regenerating
    # questions will re-ask for model/proxy on the landing page.
    st.session_state.follow_up_questions = saved_results["follow_up_questions"]
    st.session_state.systematization_answers = saved_results["systematization_answers"]
    st.session_state.systematized_concepts = [
        SystematizedConcept(**concept) for concept in saved_results["systematized_concepts"]
    ]

    st.rerun()


if __name__ == "__main__":
    main()
