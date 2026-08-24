---
status: complete
---

# Architecture: Refresh Documentation

This project is small enough for a **single architecture doc** (no `components/`).

## Approach

GitHub Pages remains MkDocs Material. Developer pages are **includes**, not copies.

`pymdownx.snippets` is already enabled in `mkdocs.yml`. Configure it so snippet paths resolve from the **repo root**:

```yaml
markdown_extensions:
  - pymdownx.snippets:
      check_paths: true
      base_path:
        - .
```

(Keep other existing markdown_extensions.)

Thin wrappers:

- `docs/using.md` — only `--8<-- "README.md"` (plus a page title if MkDocs needs one; do not restate README body).
- `docs/contributing.md` — only `--8<-- "CONTRIBUTING.md"` (same rule).

If parent-path / restrict-base-path issues appear, fix snippet config (`base_path`, `restrict_base_path`) rather than copying file contents into `docs/`.

## Nav

```yaml
nav:
  - Users:
      - Home: index.md
  - Developers:
      - Running Aspis: using.md
      - Contributing: contributing.md
      - API Reference: api.md
```

Remove `User Guide: user_guide.md`. Delete `docs/user_guide.md` once unused.

## README

Canonical usage file. Structure:

1. Existing title and badges.
2. **User section first:** short goal/why, Space URL, paper (ResearchGate + DOI). May keep or lightly adapt current intro/key-features; must explain why Aspis exists.
3. **Developer section:** remaining how-to (HF details, Docker, from-source pointer, UI, API, keys) as today.

Home (`docs/index.md`) is authored separately but should stay consistent with the README user section (same facts and links).

## Site metadata

`site_name: Aspis` can stay. Do not change Discord footer (out of scope). Do not rewrite `docs/api.md` members.

## Verification

- `uv run mkdocs build` must succeed.
- Running Aspis HTML contains README content (e.g. Docker instructions).
- Contributing HTML contains contributing content (e.g. `uv sync` / pre-commit).
- Home does not contain aieng-template phrasing.
- No separately maintained how-to body under `docs/` besides Home and the two snippet files.

No new Python modules, dependencies, or unit tests. Docs build is the check. Tests written: NA.
