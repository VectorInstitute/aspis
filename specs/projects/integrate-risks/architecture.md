---
status: complete
---

# Architecture: Integrate Risks

## Overview

Add static MIT/NIST Measure risk JSON catalogs and a small UI search layer that appends attributed risk text into the existing risk description field. No API changes.

## Data

### Files

Place under `src/aspis/data/risks/`:

- `mit_ai_risks.json` — MIT Domain Taxonomy subdomains (~24)
- `nist_ai_rmf_measure.json` — NIST AI RMF Core MEASURE subcategories (~22)

Each file is a JSON **array** of objects:

```json
{
  "id": "mit-3.1",
  "title": "3.1 False or misleading information",
  "description": "...",
  "category": "Misinformation"
}
```

`category` optional. Framework display name is derived from the file (code constant map), not stored per row.

### Loading

- Load both files once (`lru_cache`) from a CWD-relative path (`src/aspis/data/risks`); the app is run from the repo root.
- On load failure: return empty list + log; UI shows short warning.

## Modules

### `aspis.risk_catalog` (new)

Responsibilities:

- `RiskEntry` dataclass: `id`, `title`, `description`, `category`, `source` (display name), `source_key` (`mit` | `nist`)
- `load_all_risks() -> list[RiskEntry]`
- `format_dropdown_label(entry) -> str` — `SOURCE · Title — snippet…` with ~110 char budget (word-boundary truncate; skip snippet if title already long)
- `format_append_block(entry) -> str` — `[SOURCE — Title]\ndescription`
- `append_risk_text(existing: str, entry: RiskEntry) -> str` — blank-line separator if existing non-empty
- `search_risks(query: str, entries: list[RiskEntry], *, limit=10, min_chars=2) -> list[RiskEntry]` — `rapidfuzz` over title+description (+ category/source), ranked descending

Keep this UI-agnostic and unit-testable.

### `aspis.ui.main` (update)

- Add one `st_searchbox` (`streamlit-searchbox`) field **outside** the landing `st.form`, labeled `Search AI Risk Library (Optional)`.
- Search function calls `search_risks` / `format_dropdown_label` and returns `(label, RiskEntry)` tuples so picking a row appends that entry.
- On selection: stash `append_risk_text` on a non-widget session key, reset the searchbox, rerun; apply the pending text to `risk_description_input` **before** the textarea widget is instantiated.
- Keep product / risk description / model / proxy / Generate **inside** the form so Generate still flushes last-typed text.
- Do not change API routes.

## Dependencies

- Add `rapidfuzz` and `streamlit-searchbox` to project dependencies; regenerate lock with `uv lock` / `uv sync` (never hand-edit `uv.lock`).

## Error handling

- Corrupt/missing JSON: empty catalog + UI warning; free text still works.
- Empty/short query: no options / only placeholder.
- No matches: empty results list.

## Testing

- Unit tests for load (temp/fixture JSON), label formatting length rules, append separator, search ranking (typo / substring).
- Light UI test only if the project already patterns Streamlit tests; otherwise unit-test catalog helpers thoroughly.

## Non-goals

- API exposure, import feature, embeddings, custom Streamlit components.
