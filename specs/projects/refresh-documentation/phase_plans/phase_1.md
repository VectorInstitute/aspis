---
status: complete
---

# Phase 1: README user-first structure and MkDocs Users/Developers nav

## Overview

Replace aieng-template leftover copy on GitHub Pages and put a short user-facing
explanation first on both the README and Pages Home. Developer how-to on Pages
is included from `README.md` and `CONTRIBUTING.md` via `pymdownx.snippets`, not
forked into `docs/`. No new Python modules. Verification is `uv run mkdocs build`.

## Steps

1. Configure `pymdownx.snippets` in `mkdocs.yml` so includes resolve from the
   repo root. Keep other markdown_extensions. Replace the bare
   `pymdownx.snippets` entry with:

   ```yaml
   - pymdownx.snippets:
       check_paths: true
       base_path:
         - .
   ```

   If the build cannot include `../`-style or root files, set
   `restrict_base_path: false`. Do not copy README/CONTRIBUTING bodies into
   `docs/` as a workaround.

2. Replace `nav` in `mkdocs.yml` with:

   ```yaml
   nav:
     - Users:
         - Home: index.md
     - Developers:
         - Running Aspis: using.md
         - Contributing: contributing.md
         - API Reference: api.md
   ```

   Do not change `site_name`, Discord footer, theme, or `docs/api.md` members.

3. Rewrite `docs/index.md` as authored Home copy only: Aspis title; one or two
   short paragraphs on what Aspis is and why it exists (may be somewhat
   jargony: operationalizing risks, LLM-as-judge); prominent Hugging Face Space
   link `https://huggingface.co/spaces/vector-institute/aspis`; Aspis paper
   ResearchGate URL and DOI `10.13140/rg.2.2.10295.89769`. No Docker, uv,
   pre-commit, or API field lists. No paper figures, HireSight, or risk tables.
   No aieng-template phrasing.

4. Add thin snippet wrappers (page title only if needed; do not restate the
   included body):

   - `docs/using.md` — `--8<-- "README.md"`
   - `docs/contributing.md` — `--8<-- "CONTRIBUTING.md"`

5. Delete `docs/user_guide.md` (removed from nav).

6. Restructure `README.md`: keep existing title and badges; user section first
   (goal/why, Space URL, paper ResearchGate + DOI; may keep or lightly adapt
   current intro/key-features; must explain why Aspis exists; share facts/links
   with Home); then existing developer how-to (HF API details, Docker,
   from-source pointer, UI, API, keys). Do not paste CONTRIBUTING into the
   README. Adjust the `CONTRIBUTING.md` relative link if the include would 404
   on Pages (absolute GitHub URL), without forking the body. Remove any
   leftover template phrases if present (none expected).

7. Leave `CONTRIBUTING.md` content as-is (already Aspis-specific; no template
   phrases). Do not change the Hugging Face Space app.

8. Run `uv run mkdocs build`. Confirm Running Aspis HTML contains README
   developer content (e.g. Docker), Contributing HTML contains contributing
   content (e.g. `uv sync` / pre-commit), and Home HTML has no aieng-template
   phrasing.

## Tests

- NA — no new Python modules or unit tests. Docs build is the check
  (`uv run mkdocs build`).
