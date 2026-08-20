---
status: complete
---

# Functional Spec: Integrate Risks

## Goal

Help users who don’t know what to put in the **risk description** field by letting them search well-known AI risk taxonomies and insert a starting description, which they can then edit freely.

Tracked in: https://github.com/VectorInstitute/aspis/issues/93

## In scope

1. Ship curated risk data as **JSON files in this repo**, one file per source.
2. Add a **UI-only** search/select control above the existing risk description text area that appends a chosen risk (with framework attribution) into that field.
3. Rank matches with **`rapidfuzz`** (typo-tolerant, scored).

## Out of scope

- Import-risks feature (JSON layout should make it easy later; not built now).
- API / backend exposure of risk search or risk lists.
- MIT full ~1700+ risk database.
- NIST AI RMF Playbook action text; NIST GOVERN / MAP / MANAGE Core subcategories.
- Semantic / embedding search, vector DBs, or LLM-based ranking.
- Requiring a taxonomy pick (custom free text remains valid).

## Data sources

### MIT (`mit_ai_risks.json` or equivalent name)

- Content: MIT AI Risk Repository **Domain Taxonomy subdomains only** (~24 items).
- Not the full AI Risk Database.

### NIST (`nist_ai_rmf_measure.json` or equivalent name)

- Content: NIST AI RMF 1.0 **Core subcategory outcome statements** from the **MEASURE** function only (~22 items: Measure 1.x–4.x).
- Use Core wording (not Playbook).
- Rationale: Measure outcomes are the closest NIST subset to “risks you might measure”; other functions are mostly org-process outcomes and are a poor fit for Aspis’s risk description field.

### Shared JSON shape (per entry)

| Field | Required | Purpose |
|-------|----------|---------|
| `id` | yes | Stable identifier within the source file |
| `title` | yes | Short label **including section reference** (e.g. `3.1 False or misleading information`, `Measure 2.11 Fairness and bias`) |
| `description` | yes | Full risk / outcome text |
| `category` | optional | Grouping hint (e.g. MIT domain name, or `Measure 2`) |

Framework identity is **not** stored per entry — it comes from which JSON file the entry was loaded from (mapped in code to a display name such as `MIT AI Risk Repository` or `NIST AI RMF`).

Files live in-repo (exact path decided in architecture). No runtime download of taxonomies required for the feature to work.

**Appended block format** (what goes into the text area on select):

```text
[SOURCE — Title]
description
```

Examples:

```text
[MIT AI Risk Repository — 3.1 False or misleading information]
AI systems that inadvertently generate or spread incorrect or deceptive information, which can lead to inaccurate beliefs in users and undermine their autonomy. Humans that make decisions based on false beliefs can experience physical, emotional or material harms.
```

```text
[NIST AI RMF — Measure 2.11 Fairness and bias]
Fairness and bias — as identified in the map function — are evaluated and results are documented.
```

**Dropdown label format** (single line, keep scannable):

```text
SOURCE · Title — <short description snippet>…
```

Rules:
- Target about **~110 characters total** per option (hard cap ~120).
- After `SOURCE · Title`, add a short description snippet (~40–60 chars when space allows), truncated on a word boundary with `…`.
- If the title alone is already long (~90+ chars), **omit the snippet** rather than truncating the title into nonsense.
- Truncate in the dropdown only; the appended text-area block always uses the **full** title + full description.

Examples:
- `MIT · 3.1 False or misleading information — AI systems that inadvertently generate or spread incorrect or…`
- `NIST · Measure 2.11 Fairness and bias — Fairness and bias — as identified in the map function — are…`

## User flow

1. User is on the existing landing page (product + risk description + model/API settings).
2. A single **Search AI Risk Library (Optional)** autocomplete field lets them type a query (`streamlit-searchbox`; native Streamlit cannot do true typeahead in one field).
3. After a small minimum query length, matching risks from **both** sources appear as they type, ranked by `rapidfuzz` score.
4. Picking a match **appends** an attributed block to the risk description text area: framework **source** (from the file), **title** (includes section reference), and **description** (see format above). If the area already has content, append with a sensible separator (e.g. a blank line); if empty, insert the block as the initial content.
5. User may edit the text area freely afterward (including clearing or rewriting entirely).
6. User may skip search entirely and type a custom risk description, same as today.
7. Submit / generate behavior is unchanged: whatever string is in the risk description field is what Aspis uses downstream.

## UI behavior (functional)

- Pattern: one `st_searchbox` autocomplete field **outside** the landing `st.form`; pick **appends** to the risk `st.text_area` inside the form; area remains the source of truth.
- Not a native-in-text-area autocomplete widget and not a search `text_input` plus separate “Matching risks” `selectbox` / **Add selected risk** button.
- Suggestion labels use `SOURCE · Title — snippet…` with a ~110 character total budget (see format above).
- Appended text uses the attributed block format (`[SOURCE — Title]` + description), not description alone.
- Empty search / below min length: no results; text area unchanged.
- No matches: show empty results; text area unchanged; free text still allowed.
- Both sources are searched together (single search box).

## Search behavior

- Library: **`rapidfuzz`**.
- Match against **title + description** (and `category` if present), case-insensitive / fuzzy. Source display name may also be included in the searchable text.
- Practical defaults (implementation may tune slightly without a new spec):
  - Minimum query length: **2–3 characters** before showing results.
  - Maximum results shown: about **8–12**.
  - Rank by descending similarity score; drop obviously weak matches if needed for signal.

## Edge cases

| Case | Behavior |
|------|----------|
| User never uses search | Same as today; risk description is whatever they type. |
| User selects a risk then edits | Edited text is used; no link back to the taxonomy entry is required. |
| User selects again (area already has text) | New attributed block is **appended** (with separator); existing text is kept. |
| User selects when area is empty | Attributed block is inserted as the initial content. |
| Missing / corrupt JSON at runtime | Fail softly in UI (no crash of the whole app): search unavailable or empty results; free text still works. Prefer a clear short message if search cannot load. |
| Duplicate-ish titles across sources | Allowed; result labels must distinguish source. |

## Non-goals for the risk field value

- Do not separately persist taxonomy `id` into session/YAML for v1; attribution lives in the risk description text the user sees/edits.
- Downstream systematization / evaluation continues to receive a plain `risk_description` string only (which may now include framework attribution text).

## Constraints

- Keep the change **simple and short**.
- UI-only; no API contract changes.
- Prefer stock Streamlit + `rapidfuzz` over custom components.
- Data is static files in the repo (CC BY / public NIST text as applicable); no live fetch required at request time.

## Success criteria

- A new user can type a few characters (e.g. `bias`, `privacy`, `misinfo`), see ranked MIT/NIST Measure suggestions, pick one, optionally edit, and generate questions using that text.
- Custom risk descriptions without using search still work unchanged.
