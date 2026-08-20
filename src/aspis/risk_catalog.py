"""Load and search curated AI risk taxonomy catalogs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process

from aspis.logging import logger


RISKS_DIR = Path("src/aspis/data/risks")

DROPDOWN_TARGET_LEN = 110
DROPDOWN_HARD_CAP = 120
TITLE_LONG_THRESHOLD = 90
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_MIN_CHARS = 2
DEFAULT_SCORE_CUTOFF = 40


class RiskSource(Enum):
    """Known risk catalog sources and their display metadata."""

    MIT = ("MIT AI Risk Repository", "MIT", "mit_ai_risks.json")
    NIST = ("NIST AI RMF", "NIST", "nist_ai_rmf_measure.json")

    display_name: str
    short_name: str
    filename: str

    def __init__(self, display_name: str, short_name: str, filename: str) -> None:
        """Attach display metadata and catalog filename to each source."""
        self.display_name = display_name
        self.short_name = short_name
        self.filename = filename


@dataclass(frozen=True)
class RiskEntry:
    """A single risk taxonomy entry with its source attribution."""

    id: str
    title: str
    description: str
    category: str | None
    source: str
    source_key: RiskSource


def _load_source_file(source: RiskSource) -> list[RiskEntry]:
    """Load risk entries from one packaged JSON file.

    Args:
        source: Catalog source to load.

    Returns:
        Parsed entries, or an empty list if the file is missing or corrupt.
    """
    path = RISKS_DIR / source.filename
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to load risk catalog from %s", path)
        return []

    if not isinstance(raw, list):
        logger.error("Risk catalog %s is not a JSON array", path)
        return []

    try:
        return [
            RiskEntry(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                category=item.get("category"),
                source=source.display_name,
                source_key=source,
            )
            for item in raw
        ]
    except (TypeError, ValueError, KeyError):
        logger.exception("Failed to parse risk catalog from %s", path)
        return []


@lru_cache(maxsize=1)
def load_all_risks() -> list[RiskEntry]:
    """Load all risk catalogs once.

    Returns:
        Combined list of risk entries. Missing or corrupt files contribute no entries.
    """
    entries: list[RiskEntry] = []
    for source in RiskSource:
        entries.extend(_load_source_file(source))
    return entries


def _truncate_on_word_boundary(text: str, max_len: int) -> str:
    """Truncate text to max_len on a word boundary, appending an ellipsis."""
    if len(text) <= max_len:
        return text
    if max_len <= 1:
        return "…"
    truncated = text[: max_len - 1].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return f"{truncated.rstrip(' —-')}…"


def format_dropdown_label(entry: RiskEntry) -> str:
    """Format a single-line dropdown label with a ~110 character budget.

    Args:
        entry: Risk entry to label.

    Returns:
        Label like ``SOURCE · Title — snippet…``.
    """
    prefix = f"{entry.source_key.short_name} · {entry.title}"
    if len(prefix) >= TITLE_LONG_THRESHOLD:
        return _truncate_on_word_boundary(prefix, DROPDOWN_HARD_CAP)

    separator = " — "
    remaining = DROPDOWN_TARGET_LEN - len(prefix) - len(separator)
    if remaining < 20:
        return _truncate_on_word_boundary(prefix, DROPDOWN_HARD_CAP)

    snippet = _truncate_on_word_boundary(entry.description, remaining)
    label = f"{prefix}{separator}{snippet}"
    if len(label) > DROPDOWN_HARD_CAP:
        return _truncate_on_word_boundary(label, DROPDOWN_HARD_CAP)
    return label


def format_append_block(entry: RiskEntry) -> str:
    """Format the attributed block inserted into the risk description field.

    Args:
        entry: Risk entry to format.

    Returns:
        ``[SOURCE — Title]`` plus description on the next line.
    """
    return f"[{entry.source} — {entry.title}]\n{entry.description}"


def append_risk_text(existing: str, entry: RiskEntry) -> str:
    """Append an attributed risk block to existing risk description text.

    Args:
        existing: Current risk description field value.
        entry: Risk entry to append.

    Returns:
        Updated text with a blank-line separator when ``existing`` is non-empty.
    """
    block = format_append_block(entry)
    stripped = existing.strip()
    if not stripped:
        return block
    return f"{stripped}\n\n{block}"


def _searchable_text(entry: RiskEntry) -> str:
    """Build the fuzzy-search haystack for one entry."""
    parts = [entry.title, entry.description, entry.source, entry.source_key.short_name]
    if entry.category:
        parts.append(entry.category)
    return " ".join(parts)


def search_risks(
    query: str,
    entries: list[RiskEntry],
    limit: int = DEFAULT_SEARCH_LIMIT,
    min_chars: int = DEFAULT_MIN_CHARS,
    score_cutoff: float = DEFAULT_SCORE_CUTOFF,
) -> list[RiskEntry]:
    """Rank risk entries by fuzzy match against title, description, and metadata.

    Args:
        query: User search string.
        entries: Catalog entries to search.
        limit: Maximum number of results to return.
        min_chars: Minimum query length before searching.
        score_cutoff: Minimum rapidfuzz score to keep a match.

    Returns:
        Matching entries ranked by descending similarity score.
    """
    normalized = query.strip()
    if len(normalized) < min_chars or not entries:
        return []

    choices = {_searchable_text(entry): entry for entry in entries}
    matches = process.extract(
        normalized,
        choices.keys(),
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=score_cutoff,
    )
    return [choices[matched_text] for matched_text, _score, _idx in matches]
