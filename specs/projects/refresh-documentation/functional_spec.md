---
status: complete
---

# Functional Spec: Refresh Documentation

Replace template leftover copy on GitHub Pages. README and GitHub Pages both
lead with a user-facing explanation, then developer material. Do not change
the Hugging Face Space.

Supersedes the longer paper-derived user copy in the project overview: the
user-facing explanation is one or two short paragraphs (goal and why Aspis
exists), plus links to the Space and the paper. No methodology walkthrough,
worked example, or risk-category table. Developer how-to on Pages is not a
second independently maintained write-up: it is included from `README.md`
and `CONTRIBUTING.md`.

## Goals

- GitHub Pages at https://vectorinstitute.github.io/aspis/ is about Aspis,
  not the Vector AI Engineering / aieng template ([issue #101](https://github.com/VectorInstitute/aspis/issues/101)).
- Users can understand what Aspis is for and where to try it without reading
  contributor setup.
- Developers can run, contribute, and look up Python APIs from a dedicated
  docs section.
- Developer instructions on GitHub Pages stay in lockstep with `README.md`
  and `CONTRIBUTING.md`: if those files change, Pages reflects the change
  on the next docs deploy (include/transclude, not a forked copy).

## Out of scope

- Any change to the Hugging Face Space app or its hosted API.
- Paper screenshots or figures.
- Fixing the Discord footer link (currently 404).
- Rewriting the auto-generated mkdocstrings API reference (keep `docs/api.md`
  as-is aside from nav placement).
- Expanding user copy into the three-step Wallach pipeline, HireSight, or
  the paper’s risk table.
- Changing docs CI beyond what is required for new markdown / nav files
  (existing `docs.yml` already deploys `mkdocs` on markdown and `mkdocs.yml`
  changes).

## Audiences and information architecture

### GitHub Pages (MkDocs)

Two top-level sections (Material `navigation.tabs` is already enabled — this
is the easy split).

**Users**

- **Home** (`docs/index.md`): user-facing intro only (this page is authored
  for Pages, not transcluded).
  - Title/branding for Aspis (not the template).
  - One or two short paragraphs: what Aspis is for and **why it exists**.
    Copy may be somewhat technical/jargony; do not strip domain language
    just to sound simpler. Do not dump the full paper pipeline, example, or
    tables.
  - Prominent link to the hosted Space:
    https://huggingface.co/spaces/vector-institute/aspis
  - Citation of the Aspis paper with both:
    - ResearchGate: https://www.researchgate.net/publication/404299934_Aspis_Systematizing_AI_Risk_Evaluation_for_LLMs_and_Agents_Using_LLM-Based_Evaluators
    - DOI: https://doi.org/10.13140/rg.2.2.10295.89769
  - No Docker, uv, pre-commit, or API field lists on this page.

**Developers**

These pages must **include** the repo files, not rephrase them. MkDocs already
has `pymdownx.snippets`; use that (or equivalent include) so a README or
CONTRIBUTING edit is what authors maintain, and Pages updates when docs
deploy.

- **Running Aspis** (`docs/using.md` or renamed `user_guide.md`): transclude
  `README.md`. That is the body of this page. Do not maintain a parallel
  how-to in `docs/`.
- **Contributing** (`docs/contributing.md`): transclude `CONTRIBUTING.md`.
  Same rule: the markdown in the repo root is the source of truth.
- **API Reference**: existing mkdocstrings pages; do not rewrite member docs.

If README or CONTRIBUTING overlap (e.g. both mention running the UI), that
overlap may appear on Pages as well. Do not invent a third merged version
in `docs/` to “clean it up.”

Suggested `mkdocs.yml` nav shape (names can be tweaked as long as the split
holds):

```yaml
nav:
  - Users:
      - Home: index.md
  - Developers:
      - Running Aspis: using.md
      - Contributing: contributing.md
      - API Reference: api.md
```

Replace `docs/user_guide.md` template content. Either rename that file to
`using.md` (and drop template prose) or overwrite it; do not leave aieng
template pages in the nav.

### README

Canonical file for product usage (and the Running Aspis docs page). Same order
as Pages overall: user-facing section first, then developer-facing.

1. Existing badges and title may stay.
2. **Users:** one–two paragraphs on goal and why Aspis exists, Space link,
   and paper (ResearchGate + DOI). May share wording with Home; keep it
   consistent if duplicated.
3. **Developers:** the how-to that today lives in the README (Docker,
   from-source, UI, API keys, etc.). This is what Developers → Running Aspis
   shows via include.

Do not paste the full contributing guidelines into the README; those stay in
`CONTRIBUTING.md` and appear on Pages via the Contributing include.

## Copy constraints

- User paragraphs stay short. They must explain **why Aspis exists**. They
  may be a bit jargony (LLM-as-judge, operationalizing risks, etc.); do
  not flatten that into generic “try our tool” copy. Still do not paste the
  full paper methods, HireSight example, or risk table on Home.
- Developer content on Pages is whatever is in `README.md` /
  `CONTRIBUTING.md`. Keep those files aligned with current product behavior
  (models, ports, `proxy_base_url`, form fields) — not the older paper
  appendix (`openai_api_key`, GPT-4o-only).
- Remove leftover template phrases (“bootstrap AI Engineering project
  repositories”, “Use this template”, aieng-template workflow links, etc.)
  from authored docs pages (Home) and from README/CONTRIBUTING if they
  appear there.

## Edge cases

- **Link rot:** paper must be cited with DOI and ResearchGate so either
  landing still works.
- **Drift:** do not copy README/CONTRIBUTING into `docs/` as independently
  edited text. Includes must resolve from the repo root so `mkdocs build`
  and docs CI pick up README/CONTRIBUTING changes.
- **Included markdown:** README badges, relative links, and headings must
  still render acceptably on Pages (adjust README links if the include
  would otherwise 404 on the docs site, without forking the body).
- **Stale `docs/index.md` / `docs/user_guide.md`:** those files are
  currently template text; they must be fully replaced or removed from nav,
  not patched with a paragraph on top.
- **Build:** `uv run mkdocs build` must succeed after nav/file changes
  (broken nav paths are a failure).

## Success criteria

- Visiting GitHub Pages Home does not mention the AI Engineering template.
- A non-developer can find what Aspis is, why it exists, the Space, and the
  paper from Home and from the README without reading developer pages.
- A developer can find run instructions, contributing rules, and API
  reference under the Developers section.
- Hugging Face Space is unchanged by this work.
- Editing `README.md` or `CONTRIBUTING.md` changes the corresponding
  Developers pages on the next docs deploy, without a separate docs-only
  rewrite of that content.
