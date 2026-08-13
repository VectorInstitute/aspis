# Plan: Optional `proxy_base_url` + public provider endpoints

**Date:** 2026-08-12
**Status:** approved for implementation

## Goal

Surface an optional `proxy_base_url` (“Proxy address”) in the UI and API so Aspis works for the general public (direct OpenAI / Google / Anthropic OpenAI-compatible endpoints) while still supporting power users with a custom proxy (e.g. Vector).

## Decisions

1. **One URL per provider (not one global Vector default).** Keep the single OpenAI SDK client; change only `base_url`, API key, and model ID.
2. **Provider defaults** (used when the model is a known `ModelInfo` value and no override is set):

   | Provider  | Default `proxy_base_url` |
   |-----------|--------------------------|
   | OpenAI    | `https://api.openai.com/v1` |
   | Google    | `https://generativelanguage.googleapis.com/v1beta/openai/` |
   | Anthropic | `https://api.anthropic.com/v1/` |

3. **Resolution order:** non-empty request `proxy_base_url` → else `ASPIS_OPENAI_BASE_URL` (deploy override) → else provider default from known model.
4. **Vector is a power-user override:** expand advanced settings and set `proxy_base_url` to `https://proxy.vectorinstitute.ai/v1` with a Vector key.
5. **Field name:** `proxy_base_url` / label “Proxy address”.
6. **UI:** proxy field collapsed by default inside a “Proxy details” expander, always empty (placeholder “Type your proxy address”). Validate URL only when the field is non-empty (no host allowlist). See “Final UI decisions” below — there is no prefill.
7. **Custom model text (UI):** `st.selectbox(..., accept_new_options=True)`. If the user types a value that is not a known `ModelInfo` option, **`proxy_base_url` is required**.
8. **API model + proxy rules:** `model` is a string. If it **exact-matches** a `ModelInfo` enum value (`model_id`), `proxy_base_url` is optional (provider default applies). If it does **not** exact-match an enum value, `proxy_base_url` is **required**.
9. **YAML:** persist `model_id` used to generate the data; do **not** persist proxy.
10. **Explicitly in scope extras:** naming (`proxy_base_url`) and tests.
11. **Explicitly out of scope:** docs overhaul, SSRF allowlist, URL normalization beyond non-empty URL validation, auth education copy, YAML proxy persistence.

## Final UI decisions (2026-08-12, after live review)

These supersede the UI parts of decisions 6 and 7 above.

1. **Everything lives inside `st.form("input_form")`.** Streamlit only flushes text typed
   immediately before a click when the widget belongs to the submitted form; widgets outside
   a form lose the pending edit on the first click (verified in a live browser and with
   standalone probe apps — injected JavaScript does not fix it).
2. **No proxy prefill.** Form widgets do not rerun the script until submit, so a live prefill
   on model change is impossible. The proxy field always starts empty with the placeholder
   “Type your proxy address”. Accepted trade-off.
3. **Proxy control is `st.expander("Proxy details")`**, collapsed by default, replacing the
   reveal checkbox. The widget is always instantiated, so a typed value is submitted even if
   the expander is collapsed again.
4. **Layout:** borderless form containing a bordered container with the product and risk text
   areas (“the box”), then below it the caption, the model selectbox / API key columns
   (`[0.3, 0.7]`), the proxy expander, and the submit button.
5. **Validation:** known model + empty proxy → provider default (store `None`); known model +
   non-empty proxy → validate and use it; custom model ID + empty proxy → error “Please enter a
   proxy address for custom model IDs.”; custom model ID + non-empty proxy → validate and use it.

## Implementation steps

### 1. Core (`inferencer.py`)

- Add provider / default base URL metadata on `ModelInfo` (or a small adjacent map).
- Keep `DEFAULT_PROXY_BASE_URL` / Vector URL available as a known constant for power users / docs in code comments if still useful; stop using Vector as the implicit public default when a known model is selected.
- Extend `create_openai_client` (and call chain: `execute_samples_against_model`, `evaluate_text`, systematization helpers) with optional `proxy_base_url: str | None`.
- Resolve effective base URL per the order above.
- Accept model as known `ModelInfo` or free-form `model_id: str` as needed by API/UI wiring.

### 2. API (`api/main.py`)

- Add optional form field `proxy_base_url`.
- Accept `model` as string.
- Enforce: non-enum model ⇒ `proxy_base_url` required; non-empty proxy ⇒ basic URL validation.
- Thread into evaluation.

### 3. UI (`ui/main.py`)

- Model `selectbox` with `accept_new_options=True` (known friendly names + custom typed model ID).
- “Proxy details” expander holding the always-empty “Proxy address” field; required for custom text.
- Validate non-empty proxy as URL; require proxy when model is custom.
- Persist `model_id` into downloaded YAML; optionally restore if present on upload (do not require it for old files).

### 4. Tests

- Provider default resolution, env override, per-request override.
- Custom model requires proxy (UI + API).
- Enum-matching model allows omitted proxy (API).
- Empty proxy skips validation; non-empty invalid URL rejected.
- YAML includes `model_id`.

## Out of scope

- README/CONTRIBUTING rewrite (beyond what tests/code need).
- SSRF host allowlists.
- Aggressive URL rewriting/normalization.
- Storing `proxy_base_url` in YAML.
