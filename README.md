# 🛡️ Aspis

----------------------------------------------------------------------------------------

[![code checks](https://github.com/VectorInstitute/aspis/actions/workflows/code_checks.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/code_checks.yml)
[![integration tests](https://github.com/VectorInstitute/aspis/actions/workflows/integration_tests.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/integration_tests.yml)
[![docs](https://github.com/VectorInstitute/aspis/actions/workflows/docs.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/docs.yml)
[![codecov](https://codecov.io/gh/VectorInstitute/aspis/graph/badge.svg?token=nKpBEtl2Ah)](https://codecov.io/github/VectorInstitute/aspis)
![GitHub License](https://img.shields.io/github/license/VectorInstitute/aspis)


## 🧑🏿‍💻 Developing

### Installing dependencies

The development environment can be set up using
[uv](https://github.com/astral-sh/uv?tab=readme-ov-file#installation). Hence, make sure it is
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

### Running the app

Aspis runs in a [Streamlit](https://streamlit.io/) container. To execute it, use the command below:

```bash
streamlit run src/aspis/ui/main.py
```

The app will be available at `http://localhost:8501`.

After filling up all the fields, the app will offer the option to download the results as a
`.yaml` file, if you so wish.


### Running the API

Aspis also has an API that can run endpoints for evaluations. To start the API server,
use the command below:

```bash
fastapi dev src/aspis/api/main.py
```

The API will be available at port `8080`.

The main endpoint is `http://localhost:8000/evaluate_from_file`. It is a `POST` REST API
endpoint that takes a form data with the following fields:
 - An string input text `text_to_evaluate`
 - An `openai_api_key` to access the models
 - A file upload `systematized_concepts_file`, which can be downloaded after answering all the questions from the main app.

To see the full documentation for the available endpoints, you can access
`http://localhost:8000/docs` on your browser.
