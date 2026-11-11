"""In-app announcements loaded from data/announcements.json.

The file is the source of truth (Plan B): publishing a notice is a normal
commit + redeploy, with no database write. Each entry has a monotonically
increasing ``version``; the per-user ``user_config.notice_version`` stores the
highest version the user has acknowledged, so unseen notices can be derived
with a pure function.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ANNOUNCEMENTS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "announcements.json"
)


@dataclass(frozen=True)
class Announcement:
    """One published notice; versions are immutable once released."""

    version : int
    title : str
    date : str = ""
    body : str = ""
    items : tuple[str, ...] = ()


def _parse_entry(raw : object) -> Announcement | None:
    """Return a valid Announcement, or None for a malformed entry."""
    if not isinstance(raw, dict):
        return None

    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
        return None

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        return None

    date = raw.get("date", "")
    if not isinstance(date, str):
        date = ""

    body = raw.get("body", "")
    if not isinstance(body, str):
        body = ""

    raw_items = raw.get("items", [])
    items = (
        tuple(item for item in raw_items if isinstance(item, str))
        if isinstance(raw_items, list)
        else ()
    )

    return Announcement(
        version = version,
        title = title.strip(),
        date = date.strip(),
        body = body,
        items = items,
    )


def parse_announcements(payload : object) -> tuple[Announcement, ...]:
    """Validate an already-decoded payload, dropping malformed entries."""
    if isinstance(payload, dict):
        raw_entries = payload.get("announcements", [])
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        return ()

    if not isinstance(raw_entries, list):
        return ()

    by_version : dict[int, Announcement] = {}
    for raw in raw_entries:
        entry = _parse_entry(raw)
        if entry is None or entry.version in by_version:
            continue
        by_version[entry.version] = entry

    return tuple(sorted(by_version.values(), key=lambda entry: entry.version))


def parse_announcements_text(text : str) -> tuple[Announcement, ...]:
    """Parse the JSON document as text; malformed JSON degrades to empty."""
    try:
        payload = json.loads(text)
    except ValueError:
        return ()
    return parse_announcements(payload)


def load_announcements(
    path : Path | None = None,
) -> tuple[Announcement, ...]:
    """Load and validate the announcements file, sorted by version.

    A missing, unreadable or malformed file degrades to an empty tuple so a
    bad content edit can never take the whole app down.
    """
    target = path or ANNOUNCEMENTS_PATH
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return ()
    return parse_announcements_text(text)


def pending_announcements(
    announcements : tuple[Announcement, ...],
    seen_version : int,
) -> tuple[Announcement, ...]:
    """Return notices newer than the version the user has acknowledged."""
    return tuple(
        entry for entry in announcements if entry.version > seen_version
    )
