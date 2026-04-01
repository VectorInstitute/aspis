# Contributing to Aspis

Thanks for your interest in contributing to the Aspis project!

To submit PRs, please fill out the PR template along with the PR. If the PR
fixes an issue, don't forget to link the PR to the issue!

## Pre-commit hooks

Once the python virtual environment is setup, you can run pre-commit hooks using:

```bash
pre-commit run --all-files
```

## Coding guidelines

For code style, we recommend the [PEP 8 style guide](https://peps.python.org/pep-0008/).

For docstrings we use [Google format](https://google.github.io/styleguide/pyguide.html#docstrings).

We use [ruff](https://docs.astral.sh/ruff/) for code formatting and static code
analysis. Ruff checks various rules including
[flake8](https://docs.astral.sh/ruff/faq/#how-does-ruff-compare-to-flake8). The pre-commit
hooks show errors which you need to fix before submitting a PR.

Last but not the least, we use type hints in our code which is then checked using
[mypy](https://mypy.readthedocs.io/en/stable/).


## 👩‍💻 Running From Source

### 🔧 Installing the Dependencies

The development environment can be set up using
[uv](https://github.com/astral-sh/uv?tab=readme-ov-file#installation). Ensure it is
installed and then run:

```bash
uv sync
source .venv/bin/activate
```

In order to install dependencies for testing (codestyle, unit tests, integration tests),
run:

```bash
uv sync --dev
source .venv/bin/activate
```

### 🖥 Running the UI

Aspis UI runs in a [Streamlit](https://streamlit.io/) container. To execute it, use
the command below:

```bash
streamlit run src/aspis/ui/main.py
```

The app will be available at `http://localhost:8501`.

It will ask you for your AI product description and the risk you want to measure in
order to produce LLM prompts that can be used to evaluate the product's outputs against
the risk (i.e. measurement instruments).

After filling up all the fields, the app will offer the option to download the results as a
`.yaml` file so you can load the results later or use them in the API (described below).


### 🔌 Running the API

Aspis also has an API that can run endpoints for evaluations. To start the API server,
use the command below:

```bash
fastapi dev src/aspis/api/main.py
```

The API will be available at port `8000`.

The main endpoint is `http://localhost:8000/evaluate_from_file`. It is a `POST` REST API
endpoint that takes a form data with the following fields:
- An string input text `text_to_evaluate`
- An `openai_api_key` to access the models
- A file upload `systematized_concepts_file`, which can be downloaded after answering
all the questions from the main app.

To see the full documentation for the available endpoints, you can access
`http://localhost:8000/docs` on your browser.
