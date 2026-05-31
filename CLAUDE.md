# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Greyhawk** is a Python utility for analyzing images using OpenAI's vision API (gpt-4o-mini). It provides two interfaces:
- `src/analyze_image_url.py` — analyze images from URLs
- `src/analyze_image_local.py` — analyze local image files (with base64 encoding)

## Setup and Dependencies

The project requires the OpenAI Python SDK:
```bash
pip install openai
```

The API key must be stored in a `.env` file (not committed to version control):
```bash
OPENAI_API_KEY=your_key_here
```

## Running Scripts

Both scripts can be run directly from the command line:
```bash
python src/analyze_image_url.py
python src/analyze_image_local.py
```

Or imported as modules:
```python
from src.analyze_image_url import analyze_image_from_url
from src.analyze_image_local import analyze_image_from_file
```

## Code Structure

- `src/` — Core analysis modules. Each script is self-contained with a main function and CLI entry point.
- `data/`, `docs/` — Empty directories reserved for future use (image samples, documentation).

## Audio Session Recorder

`src/run.py` is the single entry point for all session recording and Slack posting.

**Setup:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

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

**Module structure:**
```
bin/
  record_session                      # thin CLI shim (executable)
src/
  session_audio_notetaker/
    __init__.py                       # exports GreyhawkSession
    session.py                        # GreyhawkSession class + all logic
    __main__.py                       # enables python -m session_audio_notetaker
```

**Architecture:**
`GreyhawkSession` runs three threads from a single process:
- `recorder` — audio capture + Whisper transcription → `transcript.txt` (fsync on each chunk)
- `summary` — reads new transcript lines every 2 min, generates a Duke Mockingbird update, writes to `updates.jsonl` and queues for Slack
- `slack` — drains an in-process `queue.Queue`, posts each item to Slack via `slack_sdk`

Events are written to `data/sessions/<date>/updates.jsonl` (one JSON object per line: `{type, timestamp, content}`) as a durable log. Event types: `session_start`, `periodic_update`, `session_complete`.

The final `session_complete` summary is posted directly by the main thread after joining the recorder — not via the queue — to guarantee delivery on shutdown.

Requires in `.env`: `OCI_API_KEY`, `OCI_OPENAI_BASE_URL`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL` (defaults to `#campaign-notes`).

**Summary Voice:**
Both periodic (2-min) and final session summaries are written in the voice of Duke Mockingbird, a warm, irreverent tabletop RPG chronicler. Summaries use parenthetical asides, admit gaps in memory, acknowledge game mechanics as story elements, and drop cliffhangers. The periodic updates are brief (2-3 sentences); the final summary is longer and structured as flowing prose.

## Notes for Future Development

- Consider adding error handling for network errors and API rate limits in the recorder.
- The current image analysis scripts use hardcoded models (gpt-4o-mini); make configurable if needed.
