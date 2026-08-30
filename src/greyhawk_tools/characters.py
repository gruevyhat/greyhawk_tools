"""Reading the party roster out of `data/characters/`.

Two character-sheet schemas are in play, because the exports came from
different capture passes:

  flat   — {"character": {"name": ...}, "classes": [{"name", "level"}]}
  2024   — {"identity": {"name": ...}, "progression": {"classes": [{"id", "level"}]}}

`load_party()` reads whichever is present and returns a uniform summary. It
never raises on a malformed file: character context is a nice-to-have for
summaries, not something worth aborting a live recording over.
"""

import json

from .paths import CHARACTERS_DIR


def _summarize(data: dict) -> str | None:
    """Render one character sheet as 'Name (Class N / Class N)'."""
    if "identity" in data:  # 2024 schema
        name = data["identity"].get("name")
        classes = data.get("progression", {}).get("classes", [])
        levels = [f"{c.get('id', '?').replace('_', ' ').title()} {c.get('level')}" for c in classes]
    else:  # flat schema
        name = data.get("character", {}).get("name")
        classes = data.get("classes", [])
        levels = [f"{c.get('name')} {c.get('level')}" for c in classes]

    if not name:
        return None
    return f"{name} ({' / '.join(levels)})" if levels else name


def load_party() -> list[str]:
    """Summarize every character sheet in `data/characters/`, sorted by filename."""
    if not CHARACTERS_DIR.is_dir():
        return []

    party = []
    for path in sorted(CHARACTERS_DIR.glob("*.json")):
        try:
            with open(path) as f:
                summary = _summarize(json.load(f))
        except (OSError, ValueError, AttributeError) as e:
            print(f"[!] Skipping character file {path.name}: {e}", flush=True)
            continue
        if summary:
            party.append(summary)
    return party
