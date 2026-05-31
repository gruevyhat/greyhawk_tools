# greyhawk_tools

Utilities for running and documenting tabletop RPG sessions in the World of Greyhawk.

## Tools

### Session Audio Notetaker

Records live gaming sessions through the microphone, transcribes audio in real-time using local Whisper, generates periodic and end-of-session summaries in the voice of **Duke Mockingbird** (a warm, irreverent campaign chronicler), and posts updates to Slack.

**Setup:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
OCI_API_KEY=your_key
OCI_OPENAI_BASE_URL=your_base_url
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#campaign-notes
```

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

Analyze images via OpenAI's vision API (gpt-4o-mini):

```bash
python src/analyze_image_url.py
python src/analyze_image_local.py
```

## Project Layout

```
bin/
  record_session          # CLI entry point
src/
  session_audio_notetaker/
    __init__.py
    session.py            # GreyhawkSession class
    __main__.py           # python -m session_audio_notetaker
  analyze_image_url.py
  analyze_image_local.py
data/
  sessions/               # gitignored; created at runtime
  ulfaerr.json            # optional character context for summaries
docs/                     # reserved
```

## Character Context

If `data/ulfaerr.json` exists, the structured summary includes the character's name and class levels. The file should follow the schema:

```json
{
  "character": { "name": "Ulfaerr" },
  "classes": [{ "name": "Ranger", "level": 5 }]
}
```
