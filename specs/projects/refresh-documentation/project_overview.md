---
status: complete
---

# Refresh Documentation

Update the GitHub Pages site at https://vectorinstitute.github.io/aspis/ so it
is about Aspis, not the Vector AI Engineering template. Tracked in
[issue #101](https://github.com/VectorInstitute/aspis/issues/101): remove
aieng-template lingo and use the README description as a starting point.
Also bring in relevant information from `CONTRIBUTING.md`.

Add a small user-friendly (as opposed to developer-friendly) section, on both
the README and the documentation, based on the paper *Aspis: Systematizing AI
Risk Evaluation for LLMs and Agents Using LLM-Based Evaluators* (preprint:
`Aspis_TAIGR_2026preprint.pdf`; ResearchGate:
https://www.researchgate.net/publication/404299934_Aspis_Systematizing_AI_Risk_Evaluation_for_LLMs_and_Agents_Using_LLM-Based_Evaluators).

That section should explain, in plain language, that Aspis turns abstract AI
risks into structured, use-case-specific prompts so LLM-based evaluators can
assess model outputs; that it uses established risk frameworks (MIT, NIST RMF);
and that it walks users from a product + risk description through follow-up
questions to downloadable measurement instruments and an API for judging
outputs.

Both GitHub Pages and the README should lead with a user-friendly section,
then a developer-friendly section. On GitHub Pages, those can live on
different pages if that is easy.
