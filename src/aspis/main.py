"""UI for the Aspis application."""

import streamlit as st


def main() -> None:
    """Entry point for the Aspis application."""
    st.set_page_config(page_title="Aspis", page_icon="🛡️", layout="centered")
    st.title("🛡️ Aspis")

    openai_api_key = st.session_state.get("openai_api_key", "")
    risk_description = st.session_state.get("risk_description", "")

    if not openai_api_key:
        st.markdown("Welcome to Aspis!")

        current_openai_api_key = st.text_input(
            label="Enter your Open AI API key:",
            placeholder="Paste your API key here...",
            help="Your API key is used to authenticate your requests to the Open AI API.",
            type="password",
        )

        if st.button("Next", type="primary"):
            if current_openai_api_key.strip():
                st.session_state.openai_api_key = current_openai_api_key
                st.rerun()
            else:
                st.error("Please enter an Open AI API key before proceeding.")

    elif not risk_description:
        current_risk_description = st.text_area(
            label="What is the AI risk you want to create a measurement instrument for?",
            placeholder="Enter your risk description here...",
            help=(
                "Your risk description is used to generate a risk assessment. Please describe the"
                + "AI risk your application is exposed to in order to generate a measurement instrument."
            ),
        )

        if st.button("Next", type="primary"):
            if current_risk_description.strip():
                st.session_state.risk_description = current_risk_description
                st.rerun()
            else:
                st.error("Please enter a risk description before proceeding.")


if __name__ == "__main__":
    main()
