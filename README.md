# 🛡️ Aspis

----------------------------------------------------------------------------------------

[![code checks](https://github.com/VectorInstitute/aspis/actions/workflows/code_checks.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/code_checks.yml)
[![integration tests](https://github.com/VectorInstitute/aspis/actions/workflows/integration_tests.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/integration_tests.yml)
[![docs](https://github.com/VectorInstitute/aspis/actions/workflows/docs.yml/badge.svg)](https://github.com/VectorInstitute/aspis/actions/workflows/docs.yml)
[![codecov](https://codecov.io/gh/VectorInstitute/aspis/graph/badge.svg?token=nKpBEtl2Ah)](https://codecov.io/github/VectorInstitute/aspis)
![GitHub License](https://img.shields.io/github/license/VectorInstitute/aspis)

Aspis is a tool for creating measurement instruments for AI risks. High-level
risk statements are often too generic to consistently evaluate a real-world
product. Aspis operationalizes a product and risk description into
systematized, measurable concepts and LLM-as-judge prompt templates that
evaluators can apply to model or agent outputs.

Try the hosted app on Hugging Face Spaces:

https://huggingface.co/spaces/vector-institute/aspis

The methodology is described in *Aspis: Systematizing AI Risk Evaluation for
LLMs and Agents Using LLM-Based Evaluators*
([ResearchGate](https://www.researchgate.net/publication/404299934_Aspis_Systematizing_AI_Risk_Evaluation_for_LLMs_and_Agents_Using_LLM-Based_Evaluators),
[DOI 10.13140/rg.2.2.10295.89769](https://doi.org/10.13140/rg.2.2.10295.89769)).
It builds on
["Evaluating Generative AI Systems is a Social Science Measurement Challenge"](https://arxiv.org/abs/2411.10939),
by Wallach et al.

**Key Features:**

- ⚙️ **Systematization**: Transforms background concepts (product and risk descriptions)
into well-defined, measurable systematized concepts
- 🌐 **Interactive UI**: Streamlit-based interface that guides you through the
systematization process with follow-up questions
- 🔗 **REST API**: Programmatic access for batch evaluations and integration into
existing workflows
- ⚖️ **LLM-as-a-Judge**: Generates ready-to-use prompt templates for evaluating text
against specific risk criteria


## 🤗 Accessing Aspis on Hugging Face

The API is also available under Hugging Face Spaces. To see the full documentation
on the available endpoints, please visit:

https://vector-institute-aspis.hf.space/api/docs

For more details on how to use the API, please see the
[Using the API](#using-the-api) section.


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

Please refer to the [CONTRIBUTING.md](https://github.com/VectorInstitute/aspis/blob/main/CONTRIBUTING.md) file.

## 🖥 Using the UI

Once the application is started using Docker, the UI will be available under `http://localhost:8080/`.

Upon access, it will ask you for your AI product description and the risk you want to measure in
order to produce LLM prompts that can be used to evaluate the product's outputs against
the risk (i.e. measurement instruments).

After filling up all the fields, the app will offer the option to download the results as a
`.yaml` file so you can load the results later or use them in the API (described below).

### 🔌 Using the API

The API will be available under `http://localhost:8080/api`..

The main endpoint is `http://localhost:8080/api/evaluate_from_file`. It is a `POST` REST API
endpoint that takes a form data with the following fields:
- An string input text `text_to_evaluate`
- An `api_key` to access the models
- A file upload `systematized_concepts_file`, which can be downloaded after answering
all the questions from the main app.
- (Optional) The `model` ID to use for the evaluation. Default is `gpt-4o`. Natively
supported model IDs are `gpt-4o`, `gpt-5.5`, `gpt-5.4-mini`, `gemini-3.1-pro-preview`,
`gemini-3-flash-preview`, `claude-opus-4-7`, and `claude-sonnet-4-6`. Custom model IDs
are allowed when `proxy_base_url` is provided.
- (Optional) A `proxy_base_url` OpenAI-compatible base URL. Leave empty for known models
to use their provider default. Required for custom model IDs.

To see the full documentation for the available endpoints, you can access
`http://localhost:8080/api/docs` on your browser.

### 🔑 LLM API keys

Known models call their provider's OpenAI-compatible endpoint by default (OpenAI, Google,
or Anthropic). Pass an API key that matches that destination as `api_key`.

To use a custom OpenAI-compatible proxy (for example Vector's
`https://proxy.vectorinstitute.ai/v1`), set `proxy_base_url` in the API or **Proxy
details** in the UI, and pass a key for that proxy.
