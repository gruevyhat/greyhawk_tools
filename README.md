# greyhawk

Working directory for a World of Greyhawk D&D campaign — the tools, the data, and the reference library.

## Layout

```
bin/                            # CLI entry points
  record_session
  analyze_image
src/greyhawk_tools/             # all application code
  paths.py                      # filesystem locations, anchored to repo root
  characters.py                 # party roster loading
  session_notetaker/            # live session recording + summarizing
  image_analysis/               # vision-model image captioning
data/
  characters/                   # one JSON per PC — committed
  sessions/<YYYY-MM-DD>/        # transcripts and summaries — gitignored
docs -> ~/Documents/DND/Greyhawk # campaign library — gitignored, see docs/INDEX.md
```

Three kinds of thing, kept apart on purpose: **applications** in `src/` and `bin/`, **data** in `data/`, **documents** in `docs/`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
OCI_API_KEY=your_key             # session notetaker
OCI_OPENAI_BASE_URL=your_base_url
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#campaign-notes
OPENAI_API_KEY=your_key          # image analysis
```

## Tools

### Session Audio Notetaker

Records live gaming sessions through the microphone, transcribes audio in real-time using local Whisper, generates periodic and end-of-session summaries in the voice of **Duke Mockingbird** (a warm, irreverent campaign chronicler), and posts updates to Slack.

**Record a session:**

```bash
python bin/record_session
```

- Transcribes audio in 30-second chunks via local Whisper
- Posts a Duke Mockingbird update to Slack every 2 minutes
- On Ctrl+C: writes `data/sessions/<date>/summary.md` and posts a final summary to Slack

**Post a past session's notes to Slack:**

```bash
python bin/record_session --post [YYYY-MM-DD]
```

Defaults to today's date. Posts `summary.md` if it exists, otherwise generates a summary from the transcript.

**Session output** (written to `data/sessions/<YYYY-MM-DD>/`):

| File | Contents |
|---|---|
| `transcript.txt` | Timestamped Whisper transcription |
| `summary.md` | Structured session notes (events, NPCs, decisions) |
| `updates.jsonl` | Durable event log (session_start, periodic_update, session_complete) |

### Image Analysis

Describe campaign art with a vision model (defaults to `gpt-4o-mini`; override with `OPENAI_VISION_MODEL`):

```bash
python bin/analyze_image path/to/image.png
python bin/analyze_image https://example.com/map.png --prompt "Describe this map"
```

## Character Context

Every `*.json` file in `data/characters/` is read at summary time and folded into the structured session notes as a party roster. Two sheet schemas are supported — the flat form:

```json
{
  "character": { "name": "Ulfaerr" },
  "classes": [{ "name": "Warlock", "level": 4 }]
}
```

and the richer `dnd5e-2024-character` form (`identity.name` plus `progression.classes`). Drop in a new file and it is picked up automatically; a malformed file is skipped with a warning rather than failing the session.

## Campaign Library

`docs/` is a symlink to `~/Documents/DND/Greyhawk` — rulebook scans, D&D Beyond sheet exports, character art, and lore. It is gitignored. See `docs/INDEX.md` for a description of every file.
