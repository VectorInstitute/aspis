# Plan: Replace InspectAI with OpenAI SDK via Vector Proxy

**Date:** 2026-08-10
**Branch:** `replace-inspectai-with-openai-proxy`
**Status:** complete

## Goal

Replace InspectAI-based LLM calls with the official OpenAI SDK, routed through `https://proxy.vectorinstitute.ai/v1`, while keeping multi-provider models and safe concurrent API-key handling.

## Decisions (from clarification)

1. **Multi-provider:** Keep Gemini/Claude/OpenAI models; the Vector proxy supports all of them via the OpenAI-compatible API.
2. **Auth:** Keep the existing pattern of passing `api_key` into call sites (UI/API). Do **not** write keys into process `os.environ` (unsafe under concurrency). Prefer per-call `OpenAI(api_key=..., base_url=...)` clients.
3. **Client:** Official `openai` SDK (not `langchain-openai`).
4. **Threading:** Remove `ThreadPoolExecutor` unless verification shows Streamlit still requires it. The old thread pool existed for InspectAI + Streamlit main-thread issues.
5. **Lockfile:** After `pyproject.toml` dependency changes, regenerate `uv.lock` with `uv` (e.g. `uv lock` / `uv sync`). **Never hand-edit `uv.lock`.**

## Steps

### 1. Branch

- Work on `replace-inspectai-with-openai-proxy` (created from `main`).

### 2. New LLM client layer (`inferencer.py` core)

- Add an OpenAI client factory that always creates a **new per-call client**:
  - `OpenAI(api_key=<caller-provided key>, base_url="https://proxy.vectorinstitute.ai/v1")`
  - Never set `os.environ` for keys.
- Replace InspectAI `Task` / `eval` / `generate` / `model_graded_qa` with `client.chat.completions.create(...)`.
- Replace InspectAI `Sample` with a small local type (e.g. dataclass with `input`).
- Keep `ModelInfo` and multi-provider model IDs; send those model IDs to the proxy.
- Adapt `extract_string_output` to OpenAI response content shapes as needed.
- Drop `ThreadPoolExecutor` if direct sync OpenAI calls are safe with Streamlit.

### 3. Call sites / API surface

- Update `systematization.py`, API, UI, and helpers for the new sample/client path.
- Preserve “pass `api_key` into the function” from UI form + API form.

### 4. Dependencies

- Add official `openai` SDK.
- Remove `inspect-ai`.
- Remove now-unused provider SDKs only if nothing else imports them after the switch (`anthropic`, `google-genai` are candidates to audit).
- Regenerate `uv.lock` via `uv` from `pyproject.toml` changes (no manual lock edits).
- Update CI notes that mention InspectAI (e.g. click pin comment in code checks).

### 5. Tests

- Rewrite tests that mock `inspect_ai_eval` to mock the OpenAI client instead.
- Remove InspectAI imports from tests.
- Cover that API keys are passed into the client constructor (not env), so concurrent calls cannot share/override keys.

### 6. Docs / misc

- Light README/CONTRIBUTING updates if they describe InspectAI or key setup incorrectly.
- Leave `.env` alone (secrets); wire default base URL in code (optional non-secret env override if useful).

### 7. Quality gate

- Coding agent implements + runs project checks/tests.
- Separate code-review agent reviews.
- Commit only after a clean review.
- Verify clean `git status` and summarize.

## Non-goals

- No InspectAI proxy workaround.
- No shared global client / env-based key for request auth.
- No full project re-spec; this is a `/spec task`.
