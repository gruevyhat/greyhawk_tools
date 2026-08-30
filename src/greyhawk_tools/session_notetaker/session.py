import io
import json
import os
import queue
import signal
import sys
import tempfile
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pyaudio
import whisper
import litellm
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..characters import load_party
from ..paths import session_dir

load_dotenv()

SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
CHUNK_SECONDS = 30
FRAMES_PER_CHUNK = (SAMPLE_RATE * CHUNK_SECONDS) // CHUNK_SIZE
SUMMARY_INTERVAL = 2 * 60  # seconds

DUKE_SYSTEM = """You are Duke Mockingbird, the self-appointed chronicler of tabletop RPG campaigns. You write session summaries that are accurate in their facts but irreverent in their delivery — equal parts campaign historian and after-dinner raconteur who has had exactly one too many stouts.

Your voice is warm, comedic, and conspiratorial. You address the reader directly. You use "Right." as a paragraph break when transitioning between topics. You admit gaps in memory with disarming honesty. Use parenthetical asides liberally. Acknowledge game mechanics as part of the story. Never invent facts you don't have."""


class GreyhawkSession:
    def __init__(self):
        self.api_key = os.getenv("OCI_API_KEY")
        self.api_base = os.getenv("OCI_OPENAI_BASE_URL")

        slack_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_channel = os.getenv("SLACK_CHANNEL", "#campaign-notes")
        self.slack = WebClient(token=slack_token) if slack_token else None
        if not self.slack:
            print("[!] SLACK_BOT_TOKEN not set — Slack posting disabled", flush=True)

        self.session_date = datetime.now().strftime("%Y-%m-%d")
        self.session_dir = session_dir(self.session_date)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_file = self.session_dir / "transcript.txt"
        self.summary_file = self.session_dir / "summary.md"
        self.updates_file = self.session_dir / "updates.jsonl"

        self.stop_event = threading.Event()
        self.write_lock = threading.Lock()
        self.slack_queue: queue.Queue = queue.Queue()
        self.transcript_line_position = 0

        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        print("\n[*] Stopping session...", flush=True)
        self.stop_event.set()

    # ── Transcript ────────────────────────────────────────────────────────────

    def _append_transcript(self, text: str):
        if not text:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {text}\n"
        with self.write_lock:
            with open(self.transcript_file, "a") as f:
                f.write(entry)
                f.flush()
                os.fsync(f.fileno())
        print(f"[✓] {entry.rstrip()}", flush=True)

    def _get_new_transcript(self) -> str:
        if not self.transcript_file.exists():
            return ""
        with open(self.transcript_file) as f:
            lines = f.readlines()
        new_lines = lines[self.transcript_line_position:]
        self.transcript_line_position = len(lines)
        return "".join(new_lines).strip()

    # ── Events / durable log ──────────────────────────────────────────────────

    def _emit_event(self, event_type: str, content: str, queue_for_slack: bool = True):
        """Write an event to updates.jsonl and optionally queue it for Slack."""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "content": content,
        }
        with open(self.updates_file, "a") as f:
            f.write(json.dumps(event) + "\n")
            f.flush()
            os.fsync(f.fileno())
        if queue_for_slack:
            self.slack_queue.put(content)

    # ── Slack ─────────────────────────────────────────────────────────────────

    def _post_to_slack(self, text: str):
        if not self.slack:
            return
        try:
            self.slack.chat_postMessage(channel=self.slack_channel, text=text)
        except SlackApiError as e:
            print(f"[!] Slack error: {e.response['error']}", flush=True)

    # ── LLM ──────────────────────────────────────────────────────────────────

    def _llm(self, system: str, user: str, max_tokens: int = 512) -> str:
        response = litellm.completion(
            model="openai/openai.gpt-oss-120b",
            api_base=self.api_base,
            api_key=self.api_key,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content.strip()

    def _quick_summary(self, transcript: str):
        try:
            return self._llm(
                DUKE_SYSTEM + "\n\nWrite a brief (2-3 sentence) update on what just happened. Short enough to read in a breath, with enough flavor to taste the chaos.",
                f"Transcript excerpt:\n\n{transcript}\n\nWhat just happened?",
                max_tokens=400,
            )
        except Exception as e:
            print(f"[!] Periodic summary error: {e}", flush=True)
            return None

    def _final_summary_duke(self, transcript: str):
        try:
            return self._llm(
                DUKE_SYSTEM + "\n\nWrite the full session summary as flowing prose. Open with the setting and recap. Weave together key events. Drop a cliffhanger at the end.",
                f"Full session transcript:\n\n{transcript}\n\nWrite the session summary.",
                max_tokens=1024,
            )
        except Exception as e:
            print(f"[!] Final Duke summary error: {e}", flush=True)
            return None

    def _final_summary_structured(self, transcript: str):
        party = load_party()
        prefix = f"Party includes: {'; '.join(party)}\n\n" if party else ""
        try:
            return self._llm(
                """You are a tabletop RPG session scribe. Extract and structure in Markdown:
- **Session Overview** (2-3 sentences)
- **Key Events** (bulleted list)
- **NPCs Encountered** (name, brief description)
- **Decisions Made** (bulleted list)
- **Unresolved Threads / Cliffhangers** (if any)
- **Rewards / Loot / XP** (if mentioned)
Be concise but capture the essence.""",
                f"{prefix}Here is the session transcript:\n\n{transcript}",
                max_tokens=1024,
            )
        except Exception as e:
            print(f"[!] Structured summary error: {e}", flush=True)
            return None

    # ── Threads ───────────────────────────────────────────────────────────────

    def _recorder_thread(self):
        """Capture audio, transcribe 30-second chunks, append to transcript.txt."""
        print("[*] Loading Whisper model...", flush=True)
        model = whisper.load_model("base")
        print("[✓] Whisper model loaded", flush=True)

        executor = ThreadPoolExecutor(max_workers=2)
        pending = []
        audio_buffer = []
        frames_accumulated = 0
        chunk_counter = 0

        def transcribe(frames, chunk_id):
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b"".join(frames))
            wav_buf.seek(0)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_buf.read())
                tmp_path = tmp.name
            try:
                result = model.transcribe(tmp_path, language="en")
                self._append_transcript(result["text"].strip())
            except Exception as e:
                print(f"[!] Transcription error (chunk {chunk_id}): {e}", flush=True)
            finally:
                os.unlink(tmp_path)

        p = pyaudio.PyAudio()
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=0,
            )
            print("[✓] Audio stream opened\n", flush=True)

            while not self.stop_event.is_set():
                try:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                except Exception:
                    break
                audio_buffer.append(data)
                frames_accumulated += 1
                if frames_accumulated >= FRAMES_PER_CHUNK:
                    frames = audio_buffer[:]
                    audio_buffer = []
                    frames_accumulated = 0
                    chunk_counter += 1
                    pending.append(executor.submit(transcribe, frames, chunk_counter))

            if audio_buffer:
                chunk_counter += 1
                pending.append(executor.submit(transcribe, audio_buffer[:], chunk_counter))

            stream.stop_stream()
            stream.close()
        finally:
            p.terminate()

        if pending:
            print("[*] Waiting for pending transcriptions...", flush=True)
            for future in as_completed(pending):
                try:
                    future.result(timeout=60)
                except Exception as e:
                    print(f"[!] {e}", flush=True)
        executor.shutdown(wait=True)
        print("[✓] Recorder done", flush=True)

    def _summary_thread(self):
        """Emit a periodic Duke Mockingbird update every SUMMARY_INTERVAL seconds."""
        last = time.time()
        while not self.stop_event.is_set():
            time.sleep(1)
            if time.time() - last >= SUMMARY_INTERVAL:
                new_text = self._get_new_transcript()
                if new_text:
                    summary = self._quick_summary(new_text)
                    if summary:
                        ts = datetime.now().strftime("%H:%M:%S")
                        self._emit_event("periodic_update", f"📊 [{ts}] {summary}")
                last = time.time()

    def _slack_thread(self):
        """Drain the slack_queue and post each item. Exits on None sentinel."""
        while True:
            text = self.slack_queue.get()
            if text is None:
                break
            self._post_to_slack(text)

    # ── Entry points ──────────────────────────────────────────────────────────

    def run(self):
        if not self.api_key or not self.api_base:
            raise ValueError("OCI_API_KEY and OCI_OPENAI_BASE_URL must be set in .env")

        print(f"\n[*] Greyhawk session — {self.session_date}", flush=True)
        print(f"[*] Transcript: {self.transcript_file}", flush=True)
        print(f"[*] Updates:    {self.updates_file}", flush=True)

        self._emit_event(
            "session_start",
            f"🎮 *Gaming Session Started* — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nLive transcription active. Updates every 2 minutes.",
        )

        recorder = threading.Thread(target=self._recorder_thread, name="recorder", daemon=True)
        summarizer = threading.Thread(target=self._summary_thread, name="summary", daemon=True)
        slacker = threading.Thread(target=self._slack_thread, name="slack", daemon=True)

        recorder.start()
        summarizer.start()
        slacker.start()

        self.stop_event.wait()
        recorder.join(timeout=90)

        if self.transcript_file.exists():
            with open(self.transcript_file) as f:
                full_transcript = f.read()

            if full_transcript.strip():
                print("\n[*] Generating structured summary (summary.md)...", flush=True)
                structured = self._final_summary_structured(full_transcript)
                if structured:
                    with open(self.summary_file, "w") as f:
                        f.write(structured)
                    print("[✓] summary.md written", flush=True)

                print("[*] Generating Duke Mockingbird final post...", flush=True)
                duke = self._final_summary_duke(full_transcript)
                if duke:
                    # Write to durable log but post directly — the slack_thread
                    # is keyed to stop_event so it may exit before the queue
                    # is drained; posting directly guarantees delivery.
                    self._emit_event(
                        "session_complete",
                        f"✅ *Session Complete*\n\n{duke}",
                        queue_for_slack=False,
                    )
                    self._post_to_slack(f"✅ *Session Complete*\n\n{duke}")

        self.slack_queue.put(None)
        slacker.join(timeout=10)

        print(f"\n[✓] Transcript: {self.transcript_file}")
        print(f"[✓] Summary:    {self.summary_file}")
        print(f"[✓] Updates:    {self.updates_file}")

    def post(self, date: str = None):
        """Post a past session's summary to Slack."""
        target_date = date or self.session_date
        past_dir = session_dir(target_date)
        summary_file = past_dir / "summary.md"
        transcript_file = past_dir / "transcript.txt"

        if not past_dir.exists():
            print(f"[!] No session found for {target_date}", file=sys.stderr)
            sys.exit(1)

        if summary_file.exists():
            with open(summary_file) as f:
                content = f.read()
            print(f"[*] Posting summary.md for {target_date}...", flush=True)
        elif transcript_file.exists():
            print("[*] No summary.md — generating from transcript...", flush=True)
            if not self.api_key or not self.api_base:
                raise ValueError("OCI credentials required to generate a summary")
            with open(transcript_file) as f:
                transcript = f.read()
            content = self._final_summary_duke(transcript)
            if not content:
                print("[!] Summary generation failed", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"[!] No transcript or summary found for {target_date}", file=sys.stderr)
            sys.exit(1)

        self._post_to_slack(f"📜 *Session Notes — {target_date}*\n\n{content}")
        print(f"[✓] Posted to {self.slack_channel}", flush=True)
