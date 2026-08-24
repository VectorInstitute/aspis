---
status: complete
---

# UI Design: Refresh Documentation

Small docs-site surface. Existing Material theme, logo, palette, and footer stay.

## Pages

| Section | Page | Source |
|---------|------|--------|
| Users | Home | Authored `docs/index.md` |
| Developers | Running Aspis | Transclude `README.md` |
| Developers | Contributing | Transclude `CONTRIBUTING.md` |
| Developers | API Reference | Existing `docs/api.md` (mkdocstrings) |

Drop template `user_guide.md` from the nav (delete or stop linking it).

## Navigation

Use existing Material `navigation.tabs`:

- **Users** — default landing. Only Home.
- **Developers** — Running Aspis, Contributing, API Reference.

No extra side nav groups, breadcrumbs, or new components.

## Home layout

1. Aspis title (not the template title).
2. One or two short paragraphs: what it is and why it exists (may be somewhat technical).
3. Clear link to the Hugging Face Space.
4. Paper citation: ResearchGate URL and DOI `10.13140/rg.2.2.10295.89769`.

No Docker/API/contributor commands on Home.

## Included pages

README and CONTRIBUTING render as-is (headings, badges, code blocks). Do not wrap them in a custom layout beyond a thin snippet file.
