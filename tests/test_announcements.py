"""Tests for data/announcements.json parsing and unseen-version filtering."""

import json
from pathlib import Path

import pytest

from src.announcements import (
    Announcement,
    load_announcements,
    parse_announcements_text,
    pending_announcements,
)


def _text(payload) -> str:
    return json.dumps(payload, ensure_ascii=False)


class TestLoadAnnouncements:
    def test_loads_and_sorts_by_version(self):
        entries = parse_announcements_text(
            _text(
                {
                    "announcements": [
                        {"version": 2, "title": "Second", "body": "B"},
                        {"version": 1, "title": "First", "date": "2026-11-11"},
                    ]
                }
            )
        )

        assert [entry.version for entry in entries] == [1, 2]
        assert entries[0].title == "First"
        assert entries[1].body == "B"

    def test_skips_malformed_entries_and_duplicate_versions(self):
        entries = parse_announcements_text(
            _text(
                {
                    "announcements": [
                        {"version": 1, "title": "Good"},
                        {"version": 1, "title": "Duplicate"},
                        {"version": 0, "title": "Bad version"},
                        {"version": "2", "title": "String version"},
                        {"title": "No version"},
                        "not an object",
                    ]
                }
            )
        )

        assert len(entries) == 1
        assert entries[0].version == 1
        assert entries[0].title == "Good"

    def test_accepts_a_bare_list(self):
        entries = parse_announcements_text(
            _text([{"version": 4, "title": "List form"}])
        )

        assert [entry.version for entry in entries] == [4]

    def test_missing_file_degrades_to_empty(self):
        path = Path("data") / "__missing_announcements__.json"

        assert load_announcements(path) == ()

    def test_malformed_json_degrades_to_empty(self):
        assert parse_announcements_text("{not json") == ()

    def test_unknown_top_level_shape_degrades_to_empty(self):
        assert parse_announcements_text(_text({"announcements": "oops"})) == ()
        assert parse_announcements_text(_text(42)) == ()

    def test_items_must_be_strings(self):
        entries = parse_announcements_text(
            _text(
                {
                    "announcements": [
                        {
                            "version": 1,
                            "title": "Mixed items",
                            "items": ["keep", 3, None, "also keep"],
                        }
                    ]
                }
            )
        )

        assert entries[0].items == ("keep", "also keep")

    def test_shipped_file_is_loadable(self):
        entries = load_announcements()

        assert entries
        assert all(entry.version > 0 for entry in entries)


class TestPendingAnnouncements:
    @pytest.fixture
    def entries(self):
        return (
            Announcement(version=1, title="One"),
            Announcement(version=2, title="Two"),
            Announcement(version=3, title="Three"),
        )

    def test_zero_seen_returns_everything(self, entries):
        assert pending_announcements(entries, 0) == entries

    def test_seen_version_filters_older_entries(self, entries):
        assert [entry.version for entry in pending_announcements(entries, 2)] == [3]

    def test_up_to_date_returns_nothing(self, entries):
        assert pending_announcements(entries, 3) == ()
        assert pending_announcements(entries, 99) == ()

    def test_gaps_and_empty_input_are_fine(self):
        entries = (
            Announcement(version=2, title="Two"),
            Announcement(version=5, title="Five"),
        )

        assert [entry.version for entry in pending_announcements(entries, 3)] == [5]
        assert pending_announcements((), 0) == ()
