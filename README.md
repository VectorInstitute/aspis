# 🛡️ Aspis

----------------------------------------------------------------------------------------

[![code checks](https://github.com/VectorInstitute/aspis/actions/workflows/code_checks.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/code_checks.yml)
[![integration tests](https://github.com/VectorInstitute/aspis/actions/workflows/integration_tests.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/integration_tests.yml)
[![docs](https://github.com/VectorInstitute/aspis/actions/workflows/docs.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/docs.yml)
[![codecov](https://codecov.io/gh/VectorInstitute/aspis/graph/badge.svg?token=nKpBEtl2Ah)](https://codecov.io/github/VectorInstitute/aspis)
![GitHub License](https://img.shields.io/github/license/VectorInstitute/aspis)

Aspis is a tool for creating measurement instruments for AI risks. It helps you
systematically analyze and evaluate AI-powered products by converting high-level risk
descriptions into specific, measurable concepts that can be operationalized using
LLM-as-a-judge evaluation.

**Key Features:**
- ⚙️ **Systematization**: Transforms background concepts (product and risk descriptions)
into well-defined, measurable systematized concepts
- 🌐 **Interactive UI**: Streamlit-based interface that guides you through the
systematization process with follow-up questions
- 🔗 **REST API**: Programmatic access for batch evaluations and integration into
existing workflows
- ⚖️ **LLM-as-a-Judge**: Generates ready-to-use prompt templates for evaluating text
against specific risk criteria

Aspis uses a systematization methodology to break down abstract AI risks into
concrete, evaluable concepts, enabling systematic risk assessment of AI systems.
It is based on the methodology described in the paper
["Evaluating Generative AI Systems is a Social Science Measurement Challenge"](https://arxiv.org/abs/2411.10939).


## 🤗 Accessing Aspis on Hugging Face

Aspis is hosted on Hugging Face Spaces under the URL below:

https://huggingface.co/spaces/vector-institute/aspis

The API is also available under the following URL:

https://vector-institute-aspis.hf.space/api

To see the documentation on the endpoints, please visit:

https://vector-institute-aspis.hf.space/api/docs


For more details on how to use the API, please see the
[Using the API](#-using-the-api) section.


## 🐳 Running using Docker

To run both the UI and API services using [Docker](https://docs.docker.com/engine/install/),
make sure you have Docker installed then build the image with the command below:

```bash
docker build --no-cache -t aspis:latest .
```

Once the image is built, run it with the command below:

```bash
docker run --rm -p 8080:8080 aspis:latest
```

## 👩‍💻 Running from source

Please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## 🖥 Using the UI

Once the application is started using Docker, the UI will be available under `http://localhost:8080/`.

Upon access, it will ask you for your AI product description and the risk you want to measure in
order to produce LLM prompts that can be used to evaluate the product's outputs against
the risk (i.e. measurement instruments).

After filling up all the fields, the app will offer the option to download the results as a
`.yaml` file so you can load the results later or use them in the API (described below).

### 🔌 Using the API

The API will be available under `http://localhost:8080/api`..

The main endpoint is `http://localhost:8080/evaluate_from_file`. It is a `POST` REST API
endpoint that takes a form data with the following fields:
- An string input text `text_to_evaluate`
- An `openai_api_key` to access the models
- A file upload `systematized_concepts_file`, which can be downloaded after answering
all the questions from the main app.

To see the full documentation for the available endpoints, you can access
`http://localhost:8080/api/docs` on your browser.
