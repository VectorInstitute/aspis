"""Tests for the risk catalog module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aspis import risk_catalog
from aspis.risk_catalog import (
    DROPDOWN_HARD_CAP,
    RiskEntry,
    RiskSource,
    append_risk_text,
    format_append_block,
    format_dropdown_label,
    load_all_risks,
    search_risks,
)


@pytest.fixture(autouse=True)
def clear_risk_cache() -> None:
    load_all_risks.cache_clear()
    yield
    load_all_risks.cache_clear()


def _entry(
    *,
    entry_id: str = "mit-3.1",
    title: str = "3.1 False or misleading information",
    description: str = (
        "AI systems that inadvertently generate or spread incorrect or deceptive information, "
        "which can lead to inaccurate beliefs in users and undermine their autonomy."
    ),
    category: str | None = "Misinformation",
    source: str = RiskSource.MIT.display_name,
    source_key: RiskSource = RiskSource.MIT,
) -> RiskEntry:
    return RiskEntry(
        id=entry_id,
        title=title,
        description=description,
        category=category,
        source=source,
        source_key=source_key,
    )


def test_risk_source_enum_exposes_init_attributes() -> None:
    assert RiskSource.MIT.display_name == "MIT AI Risk Repository"
    assert RiskSource.MIT.short_name == "MIT"
    assert RiskSource.MIT.filename == "mit_ai_risks.json"
    assert RiskSource.NIST.display_name == "NIST AI RMF"
    assert RiskSource.NIST.short_name == "NIST"
    assert RiskSource.NIST.filename == "nist_ai_rmf_measure.json"


def test_risks_dir_is_cwd_relative() -> None:
    assert Path("src/aspis/data/risks") == risk_catalog.RISKS_DIR


def test_load_all_risks_returns_mit_and_nist_entries() -> None:
    entries = load_all_risks()
    mit = [entry for entry in entries if entry.source_key is RiskSource.MIT]
    nist = [entry for entry in entries if entry.source_key is RiskSource.NIST]

    assert len(mit) == 24
    assert len(nist) == 22
    assert all(entry.source == RiskSource.MIT.display_name for entry in mit)
    assert all(entry.source == RiskSource.NIST.display_name for entry in nist)
    assert any(entry.id == "mit-3.1" for entry in mit)
    assert any(entry.id == "nist-measure-2.11" for entry in nist)


def test_load_all_risks_corrupt_file_fails_soft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad_dir = tmp_path / "risks"
    bad_dir.mkdir()
    (bad_dir / RiskSource.MIT.filename).write_text("{not-json", encoding="utf-8")
    (bad_dir / RiskSource.NIST.filename).write_text("[]", encoding="utf-8")
    monkeypatch.setattr(risk_catalog, "RISKS_DIR", bad_dir)

    entries = load_all_risks()
    assert entries == []


def test_load_all_risks_missing_file_fails_soft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty_dir = tmp_path / "risks"
    empty_dir.mkdir()
    monkeypatch.setattr(risk_catalog, "RISKS_DIR", empty_dir)

    entries = load_all_risks()
    assert entries == []


def test_format_dropdown_label_includes_snippet_when_space() -> None:
    label = format_dropdown_label(_entry())
    assert label.startswith("MIT · 3.1 False or misleading information — ")
    assert "…" in label or len(label) <= DROPDOWN_HARD_CAP
    assert len(label) <= DROPDOWN_HARD_CAP


def test_format_dropdown_label_skips_snippet_when_title_long() -> None:
    entry = _entry(
        title=("2.1 Compromise of privacy by obtaining, leaking or correctly inferring sensitive information"),
        description="Sensitive data leakage and inference without consent.",
    )
    label = format_dropdown_label(entry)
    assert " — " not in label
    assert label.startswith("MIT · 2.1 Compromise of privacy")
    assert len(label) <= DROPDOWN_HARD_CAP


def test_format_append_block() -> None:
    entry = _entry(
        entry_id="nist-measure-2.11",
        title="Measure 2.11 Fairness and bias",
        description="Fairness and bias — as identified in the map function — are evaluated and results are documented.",
        category="Measure 2",
        source=RiskSource.NIST.display_name,
        source_key=RiskSource.NIST,
    )
    assert format_append_block(entry) == (
        "[NIST AI RMF — Measure 2.11 Fairness and bias]\n"
        "Fairness and bias — as identified in the map function — are evaluated and results are documented."
    )


def test_append_risk_text_empty_and_existing() -> None:
    entry = _entry()
    block = format_append_block(entry)

    assert append_risk_text("", entry) == block
    assert append_risk_text("   ", entry) == block
    assert append_risk_text("Existing notes", entry) == f"Existing notes\n\n{block}"


def test_search_risks_min_chars() -> None:
    entries = [_entry()]
    assert search_risks("b", entries) == []
    assert search_risks("", entries) == []


def test_search_risks_ranks_typo_and_substring() -> None:
    entries = load_all_risks()

    bias_hits = search_risks("bias", entries)
    assert bias_hits
    assert any("bias" in entry.title.lower() or "bias" in entry.description.lower() for entry in bias_hits[:5])

    misinfo_hits = search_risks("misinfo", entries)
    assert misinfo_hits
    assert any(entry.id == "mit-3.1" for entry in misinfo_hits[:5])

    typo_hits = search_risks("privacey", entries)
    assert typo_hits
    assert any("privacy" in entry.title.lower() or "privacy" in entry.description.lower() for entry in typo_hits[:5])


def test_load_partial_when_one_file_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    risks_dir = tmp_path / "risks"
    risks_dir.mkdir()
    (risks_dir / RiskSource.MIT.filename).write_text(
        json.dumps(
            [
                {
                    "id": "mit-3.1",
                    "title": "3.1 False or misleading information",
                    "description": "Incorrect or deceptive information.",
                    "category": "Misinformation",
                }
            ]
        ),
        encoding="utf-8",
    )
    (risks_dir / RiskSource.NIST.filename).write_text("{bad", encoding="utf-8")
    monkeypatch.setattr(risk_catalog, "RISKS_DIR", risks_dir)

    entries = load_all_risks()
    assert len(entries) == 1
    assert entries[0].id == "mit-3.1"
    assert entries[0].source_key is RiskSource.MIT


def test_load_omitted_category_defaults_to_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    risks_dir = tmp_path / "risks"
    risks_dir.mkdir()
    (risks_dir / RiskSource.MIT.filename).write_text(
        json.dumps(
            [
                {
                    "id": "mit-3.1",
                    "title": "3.1 False or misleading information",
                    "description": "Incorrect or deceptive information.",
                    "unrelated": "ignored",
                }
            ]
        ),
        encoding="utf-8",
    )
    (risks_dir / RiskSource.NIST.filename).write_text("[]", encoding="utf-8")
    monkeypatch.setattr(risk_catalog, "RISKS_DIR", risks_dir)

    entries = load_all_risks()
    assert len(entries) == 1
    assert entries[0].category is None


def test_load_non_list_root_fails_soft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    risks_dir = tmp_path / "risks"
    risks_dir.mkdir()
    (risks_dir / RiskSource.MIT.filename).write_text('{"id": "mit-3.1"}', encoding="utf-8")
    (risks_dir / RiskSource.NIST.filename).write_text("[]", encoding="utf-8")
    monkeypatch.setattr(risk_catalog, "RISKS_DIR", risks_dir)

    assert load_all_risks() == []


def test_load_bad_object_fails_soft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    risks_dir = tmp_path / "risks"
    risks_dir.mkdir()
    (risks_dir / RiskSource.MIT.filename).write_text("[null]", encoding="utf-8")
    (risks_dir / RiskSource.NIST.filename).write_text(
        json.dumps([{"id": "nist-1", "extra": True}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(risk_catalog, "RISKS_DIR", risks_dir)

    assert load_all_risks() == []


def test_truncate_and_label_edge_cases() -> None:
    assert risk_catalog._truncate_on_word_boundary("abcdef", 1) == "…"
    assert risk_catalog._truncate_on_word_boundary("short", 10) == "short"

    # Prefix under the long-title threshold but with too little room for a snippet.
    mid_title = "x" * 83
    mid_label = format_dropdown_label(_entry(title=mid_title, description="Snippet omitted."))
    assert " — " not in mid_label
    assert len(mid_label) <= DROPDOWN_HARD_CAP

    # Very long description forces hard-cap truncation of the full label.
    capped = format_dropdown_label(
        _entry(
            title="Short title",
            description="word " * 80,
        )
    )
    assert len(capped) <= DROPDOWN_HARD_CAP
