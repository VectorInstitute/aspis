---
status: complete
---

# UI Design: Integrate Risks

Small addition to the existing landing page — not a new screen.

## Placement

The landing page is **not** wrapped in `st.form`, so the searchbox can sit between product and risk and still rerun as the user types. Generate is a normal `st.button`; every landing widget participates in that rerun. Follow-up questions keep their `st.form`.

Visual order (no CSS reordering):

1. Welcome copy
2. Product description (no border; original label/placeholder/help)
3. Shared risk title: `What is the AI risk you want to create a measurement instrument for?`
4. `st_searchbox` (native Streamlit cannot typeahead in one field; the custom component needs live reruns as the user types). No visible searchbox label.
5. Risk description text area (collapsed label; source of truth)
6. Model / API key / proxy / **Generate Questions**

## Search control

- Single autocomplete field spanning both MIT and NIST catalogs
- Placeholder: `Search AI Risk library (Optional, e.g. type "bias", "privacy", "misinformation"...)`
- As the user types, show ranked matches (`rapidfuzz` via `search_risks`); options labeled `SOURCE · Title — snippet…` (~110 char budget per functional spec)
- On pick: **append** the attributed block to the risk description text area (pending-append on a non-widget session key, then apply before the textarea is instantiated); reset the searchbox so the same risk can be picked again
- No separate “Matching risks” selectbox and no **Add selected risk** button
- User can skip search and type a custom risk description in the text area

## Text area

- No visible duplicate of the shared title; collapsed label only
- Placeholder: `Or enter your risk description here...`
- Value may grow via appends; user edits freely

## Visual

- Match existing Streamlit styling; no new theme or cards
- Tighten the gap between searchbox and the risk textarea as much as stock Streamlit plus a small CSS snippet allow (the searchbox is an iframe)
- Fail-soft: if catalogs fail to load, show a short message near the search control; text area still works
