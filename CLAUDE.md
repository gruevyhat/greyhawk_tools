# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Greyhawk** is the working directory for a World of Greyhawk D&D campaign in which the repo owner is a player (D&D Beyond handle `gruevyhat`). It holds three different kinds of thing, and keeping them separate is the point of the layout:

| Kind | Where | Tracked by git? |
|---|---|---|
| **Applications** — the tools that run during and after a session | `bin/`, `src/greyhawk_tools/` | yes |
| **Data** — structured campaign data the tools read and write | `data/` | characters yes, sessions no |
| **Documents** — the human-facing reference library | `docs/` (symlink) | no |

## Layout

```
bin/
  record_session                  # CLI shim → greyhawk_tools.session_notetaker
  analyze_image                   # CLI shim → greyhawk_tools.image_analysis
  simulate_combat                 # CLI shim → greyhawk_tools.combat_sim
src/
  greyhawk_tools/
    __init__.py
    paths.py                      # every filesystem location, anchored to repo root
    characters.py                 # load_party() — reads data/characters/*.json
    session_notetaker/
      __init__.py                 # exports GreyhawkSession
      session.py                  # GreyhawkSession class + all recording logic
      __main__.py                 # CLI argument parsing
    image_analysis/
      __init__.py
      analyzer.py                 # analyze() / analyze_image_from_url() / _from_file()
      __main__.py                 # argparse CLI
    combat_sim/
      __init__.py
      dice.py                     # vectorized Monte Carlo dice primitives
      character.py                # load_character() — parses actions/resources/slots out of a character JSON
      masteries.py                # shared damage mechanics (crit, Graze, GWF, Savage Attacker)
      sweep.py                    # AC-sweep DPR comparison harness
      __main__.py                 # argparse CLI
      policies/                   # one file per character: round-by-round tactics
data/
  characters/                     # one JSON per PC — committed
    ulfaerr.json
    serethe.json
    ...                          # 8 total; see data/characters/*.json
  sessions/<YYYY-MM-DD>/          # gitignored; created at runtime
    transcript.txt
    summary.md
    updates.jsonl
    recorder.log
docs -> ~/Documents/DND/Greyhawk   # gitignored symlink; see docs/INDEX.md
```

### Paths

`src/greyhawk_tools/paths.py` is the single source of truth for filesystem locations. Every path it exports is absolute, derived from `PROJECT_ROOT`, so the tools behave identically regardless of the working directory they are launched from. **Do not hardcode relative paths like `Path("data/sessions")` in modules** — that was a real bug once (a character-context lookup silently pointed at a file that had moved, and the feature died without an error).

### `docs/` — the campaign library

`docs/` is a symlink to `~/Documents/DND/Greyhawk`, a large personal folder of rulebook scans, D&D Beyond sheet exports, character art, and lore. It is gitignored and lives outside the repo. `docs/INDEX.md` describes every file in it — read that rather than listing the directory, and update it when files are added.

Structure: `rulebooks/`, `characters/{ulfaerr,sereth}/`, `lore/`, `reference/`, `unidentified/`.

### Characters

`data/characters/` holds one JSON file per character in the "Greyhawk" D&D Beyond campaign (8 as of this writing), each in the rich `dnd5e-2024-character` schema — provenance (`source: {book, page}`) on every rules element, `origin` on every character-specific value, derived numbers always `{value, formula, components}`, and unresolved fields left `null` with a matching `validation.unresolved` entry rather than guessed at. Two are the repo owner's own PCs: **Ulfraerr** (`ulfaerr.json`, Barbarian 1 / Warlock 4) and **Serethe "Se" Skarsdotr** (`serethe.json`, Goliath Paladin 4 / Sorcerer 1).

`greyhawk_tools.characters.load_party()` reads every file and returns a uniform `["Name (Class N / Class N)", ...]`. It never raises on a bad file — character context is a nice-to-have for summaries, not worth aborting a live recording over. Add a new PC by dropping a JSON file in `data/characters/`; no code change needed. (The module's docstring still describes a now-resolved flat-vs-2024-schema branch — all 12 files are 2024-schema now, so that branch is dead code, left as-is since removing it wasn't in scope for the work that made it dead.)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` in the project root (never committed):

```
OCI_API_KEY=...             # session notetaker LLM
OCI_OPENAI_BASE_URL=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#campaign-notes
OPENAI_API_KEY=...          # image analysis only
```

The combat simulator needs no `.env` entries — it only reads `data/characters/*.json`.

## Session Notetaker

**Record a live session:**

```bash
python bin/record_session
```

- Listens on the microphone; records 30-second chunks
- Transcribes each chunk with local Whisper in real-time
- Appends timestamped entries to `data/sessions/<YYYY-MM-DD>/transcript.txt`
- Every 2 minutes, generates a brief Duke Mockingbird update and posts it to Slack
- Press Ctrl+C to stop; generates both a structured `summary.md` and a final Duke Mockingbird post to Slack

**Post a past session to Slack:**

```bash
python bin/record_session --post [YYYY-MM-DD]
```

Posts the session's `summary.md` (or generates a Duke Mockingbird summary from the transcript if none exists). Defaults to today's date.

### Architecture

`GreyhawkSession` runs three threads from a single process:

- `recorder` — audio capture + Whisper transcription → `transcript.txt` (fsync on each chunk)
- `summary` — reads new transcript lines every 2 min, generates a Duke Mockingbird update, writes to `updates.jsonl` and queues for Slack
- `slack` — drains an in-process `queue.Queue`, posts each item to Slack via `slack_sdk`

Events are written to `data/sessions/<date>/updates.jsonl` (one JSON object per line: `{type, timestamp, content}`) as a durable log. Event types: `session_start`, `periodic_update`, `session_complete`.

The final `session_complete` summary is posted directly by the main thread after joining the recorder — not via the queue — to guarantee delivery on shutdown. **Preserve this invariant.**

LLM: `openai/openai.gpt-oss-120b` via `litellm` against OCI. Periodic summaries ≤400 tokens; final summaries ≤1024.

### Summary Voice

Both periodic (2-min) and final session summaries are written in the voice of Duke Mockingbird, a warm, irreverent tabletop RPG chronicler. Summaries use parenthetical asides, admit gaps in memory, acknowledge game mechanics as story elements, and drop cliffhangers. The periodic updates are brief (2-3 sentences); the final summary is longer and structured as flowing prose. The system prompt lives in `DUKE_SYSTEM` in `session.py`.

The structured `summary.md` is generated separately, by a plain scribe prompt with fixed Markdown headings, and is prefixed with the party roster from `load_party()`.

## Image Analysis

Describes campaign art with a vision model. Unlike the notetaker, this talks to OpenAI directly (`OPENAI_API_KEY`), not OCI.

```bash
python bin/analyze_image "docs/characters/sereth/art/Codex Image Aug 13, 2026, 07_33_27 PM.png"
python bin/analyze_image https://example.com/map.png --prompt "Describe this map"
```

Or as a module:

```python
from greyhawk_tools.image_analysis import analyze
analyze("path/or/url", prompt="What is in this image?")
```

Model defaults to `gpt-4o-mini`; override with `OPENAI_VISION_MODEL` in `.env`.

## Combat Simulator

Monte Carlo (numpy) DPR-vs-AC comparison across party members' weapon-attack builds, driven entirely by `data/characters/*.json` — no bespoke per-character script.

```bash
python bin/simulate_combat                                    # all characters with a registered tactics policy
python bin/simulate_combat -c serethe talon_aldric             # a subset
python bin/simulate_combat --plot data/characters/ac_sweep.png # PNG comparison chart
python bin/simulate_combat --target-save-bonus 5               # target's save bonus, for save-based spells
```

### Architecture

The engine/policy split is the load-bearing design decision:

- **Engine** (`character.py`, `dice.py`, `masteries.py`, `sweep.py`) is entirely data-driven: it parses `actions.attacks[]` (attack bonus, damage-dice string, Weapon Mastery tag), `resources[]`, `spellcasting.slots`, and — for save-based leveled spells — `spellcasting.known_spells` straight off a character's JSON, and knows the *mechanics* of crits, Great Weapon Fighting, Savage Attacker, the Weapon Mastery riders that affect single-target damage (Graze, Vex), and saving throws (`masteries.save_damage`). It never guesses at tactics.
- **Policy** (`policies/<character_id>.py`, one file each) is the genuinely per-character part: round-by-round action/bonus-action choice and resource spend order — e.g. Serethe's "Vow of Enmity round 1, Booming Blade after, spend the highest smite slot on every hit," or Finn's "Magic Missile with the highest slot available each round, Ray of Frost once dry." This can't be derived from the sheet; it's a judgment call, kept intentionally thin (~20–90 lines).

All 8 remaining characters have a policy (Drystan Elmspirit, Vicky Fistvigor, Burtha's Dad, and Gilbert the Glorious were removed from `data/characters/` entirely at the user's request — Drystan specifically because level 1 against a party otherwise levels 3-5 wasn't a meaningful comparison). Leveled spellcasting is modeled for the four caster-flagged builds: Finn (Magic Missile — a fixed PHB-2024 formula, auto-hit, hardcoded in the policy since it isn't sheet data) and Halden (Guiding Bolt, upcast +1d6/slot level, already an attack-roll spell in `actions.attacks`) spend slots highest-first each round; Eddwarn (Thunderwave) and Wimble (Dissonant Whispers) do the same with **save-based** spells via `Character.spells`/`masteries.save_damage`. All four fall back to their at-will cantrip/weapon once slots run dry. Casting a leveled spell costs the Action, so it replaces the round's normal attack entirely rather than stacking on top of it — the earlier "Ray of Frost/Starry Wisp every round" versions undercounted these four builds' actual damage.

Save-based spells need a target saving-throw bonus, which isn't the same stat as AC — `--target-save-bonus` (default 3) is a separate, explicit sweep parameter held constant across the AC axis rather than derived from it, so a save-only build's curve legitimately comes out flat against AC. That's the correct picture, not a bug. Attack-roll leveled spells (Guiding Bolt) stay AC-sensitive as normal. Talon and Gilbert were deliberately left alone — Divine Smite already **is** their leveled-casting representation, and spending their Action on Guiding Bolt instead of Extra Attack + smite would be a straight DPR loss, not a tactic. Spirit Guardians (Halden) isn't modeled — its slot economy competes with Guiding Bolt for the same pool in a way this pass didn't take on.

Validated against `inbox/level5_damage_sim_sorcerer.py` (the hand-written script this replaces) by reproducing its three builds' AC 12–25 DPR curves to within ±0.1 at n=100,000 trials — except Ulfraerr, whose curve now sits meaningfully higher because the real character sheet carries a customized magic pact weapon the original script's simplified halberd assumption didn't have (see `ulfaerr.json`'s `validation.unresolved` for the exact damage-bonus decomposition ambiguity). Re-run this comparison after touching shared engine code (`character.py`, `masteries.py`, `dice.py`) — it's cheap insurance against silently breaking the three validated builds.

## Notes for Future Development

- Consider adding error handling for network errors and API rate limits in the recorder.
- `input_device_index=0` is hardcoded in the recorder's audio stream; make configurable if the mic setup changes.
- `characters.py`'s flat-vs-2024-schema branch is now dead code (see "Characters" above) — safe to simplify once nobody's relying on the old behavior.
- The combat simulator doesn't model AoE (multiple targets) or Spirit Guardians' recurring/no-action damage — everything is single-target and costs an Action or Bonus Action explicitly. Sacred Flame/Fireball-style spells with no captured `known_spells` entry on a given sheet also aren't modeled; add the spell's `damage`/`save`/`save_dc` to the JSON (see `eddwarn_celas.json`'s `thunderwave` entry for the pattern) to bring a new one in.
