"""Canonical filesystem locations, anchored to the repository root.

Every path here is absolute, so the tools behave identically no matter which
directory they are invoked from.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
CHARACTERS_DIR = DATA_DIR / "characters"
SESSIONS_DIR = DATA_DIR / "sessions"

# `docs/` is a symlink to the campaign's reference library (rulebooks, art,
# lore, character sheet exports). It lives outside the repo and is gitignored.
DOCS_DIR = PROJECT_ROOT / "docs"


def session_dir(date: str) -> Path:
    """Directory holding one session's transcript, summary, and event log."""
    return SESSIONS_DIR / date
