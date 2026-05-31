# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

**greyhawk_tools** — utilities for recording and summarizing tabletop RPG sessions. The primary tool is a session audio notetaker that transcribes microphone input, generates summaries in the voice of Duke Mockingbird, and posts updates to Slack.

See `CLAUDE.md` for full architecture details, setup instructions, and the Duke Mockingbird persona specification.

## Key files

| Path | Purpose |
|---|---|
| `bin/record_session` | CLI entry point — adds `src/` to path, calls into the module |
| `src/session_audio_notetaker/session.py` | `GreyhawkSession` class — all recording, transcription, LLM, and Slack logic |
| `src/session_audio_notetaker/__main__.py` | CLI argument parsing |
| `requirements.txt` | Python dependencies |
| `.env` | Secrets — never commit |

## Coding conventions

- All session logic lives in `src/session_audio_notetaker/session.py`. Do not split it further without a strong reason.
- The three worker threads (`recorder`, `summary`, `slack`) share a `threading.Event` for shutdown and a `queue.Queue` for Slack messages. Do not introduce additional IPC mechanisms.
- `session_complete` is always posted to Slack directly from the main thread after joining the recorder — not via the queue — so it is guaranteed to be delivered on shutdown. Preserve this invariant.
- The `.env` file must never be committed. Secrets are loaded via `python-dotenv`.
- Session output goes to `data/sessions/<YYYY-MM-DD>/` and is gitignored.

## LLM usage

- Model: `openai/openai.gpt-oss-120b` via `litellm` with OCI credentials.
- Periodic summaries: ≤400 tokens, Duke Mockingbird voice, 2-3 sentences.
- Final session summary (Duke): ≤1024 tokens, flowing prose.
- Final session summary (structured): ≤1024 tokens, Markdown with fixed headings.

## Duke Mockingbird

The summary voice. Warm, irreverent, conspiratorial. Uses "Right." as a transition. Parenthetical asides. Admits uncertainty rather than inventing. Treats game mechanics as story events. Drops a cliffhanger at the end of every full summary. See `CLAUDE.md` for the full system prompt.
