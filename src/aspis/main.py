"""UI for the Aspis application."""

import streamlit as st

from aspis.chat import render_chat_ui


def main() -> None:
    """Entry point for the Aspis application."""
    st.set_page_config(page_title="Aspis", page_icon="🛡️", layout="centered")
    st.title("🛡️ Aspis")

    openai_api_key = st.session_state.get("openai_api_key", "")
    risk_description = st.session_state.get("risk_description", "")
    product_description = st.session_state.get("product_description", "")

    if not openai_api_key or not product_description or not risk_description:
        render_landing_page()

    else:
        render_chat_ui(
            openai_api_key=openai_api_key,
            risk_description=risk_description,
            product_description=product_description,
        )


def render_landing_page() -> None:
    """Render the landing page elements."""
    st.markdown("Welcome to Aspis!")

    with st.form("input_form"):
        # Product description text area
        current_product_description = st.text_area(
            label="What is the description of your AI-powered product?",
            placeholder="Enter your product description here...",
            help=(
                "Your product description is used to generate a measurement instrument for an AI risk."
                + "Please describe your product in a comprehensive way."
            ),
        )

        # Risk description text area
        current_risk_description = st.text_area(
            label="What is the AI risk you want to create a measurement instrument for?",
            placeholder="Enter your risk description here...",
            help=(
                "Your risk description is used to generate a risk assessment. Please describe the"
                + "AI risk your product is exposed to in order to generate a measurement instrument."
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


if __name__ == "__main__":
    main()
