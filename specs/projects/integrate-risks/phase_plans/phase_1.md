---
status: complete
---

# Phase 1: Risk catalogs, search helpers, landing UI

## Overview

Ship curated MIT Domain Taxonomy (~24) and NIST AI RMF MEASURE (~22) JSON catalogs, a UI-agnostic `aspis.risk_catalog` module (load/search/format/append), add `rapidfuzz` and `streamlit-searchbox`, and wire a single landing autocomplete field so picks append attributed blocks. Unit-test the catalog helpers thoroughly.

## Steps

1. **Dependency:** Add `rapidfuzz` and `streamlit-searchbox` to `[project].dependencies` in `pyproject.toml`; run `uv lock` then `uv sync` (never hand-edit `uv.lock`).

2. **Data files** under `src/aspis/data/risks/`:
   - `mit_ai_risks.json` — array of ~24 MIT Domain Taxonomy subdomain entries (`id`, `title` with section ref, `description`, optional `category` = domain name).
   - `nist_ai_rmf_measure.json` — array of ~22 NIST AI RMF Core MEASURE subcategory outcomes (`id`, `title` like `Measure 2.11 Fairness and bias`, `description` = Core outcome text, optional `category` like `Measure 2`).
   - Load via CWD-relative `Path("src/aspis/data/risks")` (app is run from the repo root).

3. **Module `src/aspis/risk_catalog.py`:**
   - `RiskEntry` dataclass: `id`, `title`, `description`, `category: str | None`, `source: str`, `source_key: Literal["mit", "nist"]`
   - Source display map: `mit` → `MIT AI Risk Repository`, `nist` → `NIST AI RMF`; short dropdown prefix `MIT` / `NIST`
   - `load_all_risks() -> list[RiskEntry]` — `@lru_cache`; on missing/corrupt JSON log + return `[]` (or empty for that file)
   - `format_dropdown_label(entry) -> str` — `SOURCE · Title — snippet…`, ~110 char budget, hard cap ~120; word-boundary truncate; skip snippet if title portion already long (~90+)
   - `format_append_block(entry) -> str` — `[SOURCE — Title]\ndescription` using full display source name
   - `append_risk_text(existing: str, entry: RiskEntry) -> str` — blank-line separator when existing non-empty
   - `search_risks(query, entries, *, limit=10, min_chars=2, score_cutoff=40) -> list[RiskEntry]` — `rapidfuzz` WRatio (or similar) over title+description+category+source; ranked descending

4. **UI (`src/aspis/ui/main.py`):** one `st_searchbox` field outside the form:
   - Label `Search AI Risk Library (Optional)`; placeholder `e.g. bias, privacy, or misinformation`.
   - Live typeahead via `search_risks` / `format_dropdown_label`; picking a result appends via `append_risk_text` using the pending-append-before-widget pattern, then resets the searchbox.
   - Product / risk `text_area` / model / proxy / Generate stay inside `st.form` (flush-safe with Generate).
   - Fail-soft: if catalog empty after load, show short `st.warning` near search; free text still works.
   - Keep Generate Questions path unchanged otherwise.

5. **Tests:** `tests/aspis/test_risk_catalog.py` covering load (real packaged JSON + corrupt/missing via monkeypatch), label length rules, append separator, search typo/substring ranking. No new Streamlit integration test required unless trivial; existing landing UI tests should still pass (may need to account for new widgets if they assert exact widget counts).

6. **Verify:** `pre-commit run --all-files` (or project lint/type/format), then `uv run pytest -m "not integration_test"` (and spot-check integration if UI assertions break).

## Tests

- `test_load_all_risks_returns_mit_and_nist_entries` — packaged JSON loads; counts ~24 MIT + ~22 NIST; sources set correctly
- `test_load_all_risks_missing_file_returns_empty_or_partial` — monkeypatch path / corrupt JSON fails soft
- `test_format_dropdown_label_includes_snippet_when_space` — short title gets `SOURCE · Title — snippet…` under ~120 chars
- `test_format_dropdown_label_skips_snippet_when_title_long` — long title omits snippet
- `test_format_append_block` — exact `[SOURCE — Title]\ndescription` shape
- `test_append_risk_text_empty_and_existing` — no separator when empty; blank line when existing
- `test_search_risks_min_chars` — short query returns `[]`
- `test_search_risks_ranks_typo_and_substring` — e.g. `bias` / `misinfo` / typo finds expected entries near top
