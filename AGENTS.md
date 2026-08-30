# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

The working directory for a World of Greyhawk D&D campaign in which the owner is a player. It holds three separate kinds of thing:

- **applications** — `bin/` and `src/greyhawk_tools/`
- **data** — `data/` (characters committed, sessions gitignored)
- **documents** — `docs/`, a gitignored symlink to `~/Documents/DND/Greyhawk`

The primary tool is a session audio notetaker that transcribes microphone input, generates summaries in the voice of Duke Mockingbird, and posts updates to Slack.

See `CLAUDE.md` for full architecture details, setup instructions, and the Duke Mockingbird persona specification.

## Key files

| Path | Purpose |
|---|---|
| `bin/record_session` | CLI entry point — adds `src/` to path, calls into the module |
| `bin/analyze_image` | CLI entry point for image analysis |
| `src/greyhawk_tools/paths.py` | Single source of truth for filesystem locations |
| `src/greyhawk_tools/characters.py` | `load_party()` — reads `data/characters/*.json` |
| `src/greyhawk_tools/session_notetaker/session.py` | `GreyhawkSession` — all recording, transcription, LLM, and Slack logic |
| `src/greyhawk_tools/image_analysis/analyzer.py` | Vision-model image captioning |
| `requirements.txt` | Python dependencies |
| `.env` | Secrets — never commit |
| `docs/INDEX.md` | Describes every file in the campaign library |

## Coding conventions

- **Never hardcode a relative path.** Import locations from `greyhawk_tools.paths`, which anchors everything to `PROJECT_ROOT`. A hardcoded `Path("data/ulfaerr.json")` once silently killed the character-context feature when the file moved — `.exists()` returned False and no error was raised.
- All session logic lives in `src/greyhawk_tools/session_notetaker/session.py`. Do not split it further without a strong reason.
- The three worker threads (`recorder`, `summary`, `slack`) share a `threading.Event` for shutdown and a `queue.Queue` for Slack messages. Do not introduce additional IPC mechanisms.
- `session_complete` is always posted to Slack directly from the main thread after joining the recorder — not via the queue — so it is guaranteed to be delivered on shutdown. Preserve this invariant.
- `load_party()` must never raise. Character context is optional enrichment; a malformed sheet is skipped with a warning, not escalated.
- The `.env` file must never be committed. Secrets are loaded via `python-dotenv`.
- Session output goes to `data/sessions/<YYYY-MM-DD>/` and is gitignored.
- `docs/` points outside the repo into the owner's Documents folder. Read from it freely; do not move or delete anything there without asking, and update `docs/INDEX.md` if you add files.

## LLM usage

Two different providers, deliberately:

- **Session notetaker** — `openai/openai.gpt-oss-120b` via `litellm` with OCI credentials (`OCI_API_KEY`, `OCI_OPENAI_BASE_URL`).
- **Image analysis** — OpenAI directly (`OPENAI_API_KEY`), model from `OPENAI_VISION_MODEL`, default `gpt-4o-mini`.

Token budgets: periodic summaries ≤400, final Duke summary ≤1024, final structured summary ≤1024.

## Duke Mockingbird

The summary voice. Warm, irreverent, conspiratorial. Uses "Right." as a transition. Parenthetical asides. Admits uncertainty rather than inventing. Treats game mechanics as story events. Drops a cliffhanger at the end of every full summary. The system prompt is `DUKE_SYSTEM` in `session.py`.
