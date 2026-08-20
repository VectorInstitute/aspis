---
status: complete
---

# Integrate Risks

Integrate well-known AI risk frameworks into Aspis so users who don't know what to put in the risk description field can pick (or start from) a risk from a searchable taxonomy.

**Problem:** Users often don't know what to input into the risk description field in the UI. They need help choosing an AI risk from a well-known repository.

**Sources (initially):**
- MIT AI Risk Repository
- NIST Risk Framework (NIST RMF / AI risk taxonomy as applicable)

Tracked in: https://github.com/VectorInstitute/aspis/issues/93

**Approach (keep it simple and short):**
- Transform risks from each repository into JSON files that live in this repo — **one JSON file per source** (MIT, NIST).
- That layout also makes a future "import risks" feature easy; **import is out of scope for now**.
- In the UI, the existing **risk description** text box should offer **autocomplete**: as the user types, matched risks appear in a dropdown.
- The ultimate value in that field remains **user-defined** — they can select a suggestion and then edit the text freely.
- Implementation should be as simple and short as possible.

**Working name / folder:** `integrate-risks`
