# halo/core/pipeline.py

import os
import datetime
import json
from halo.core.listener import start_stream, listen_continuous, stop_streaming

# ----------------- Transcript Cache -----------------
_transcript_cache = []

# Transcript folder
TRANSCRIPTS_DIR = os.path.join("data", "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

# Global session counter (increments each time Listen starts fresh)
_session_counter = 0
TRANSCRIPT_FILE = None


def _new_session_file():
    """
    Create a new transcript file for each Listen → Stop session.
    Example: meeting-20250907-1.txt, meeting-20250907-2.txt
    """
    global _session_counter, TRANSCRIPT_FILE, _transcript_cache
    _session_counter += 1
    today = datetime.datetime.now().strftime("%Y%m%d")
    TRANSCRIPT_FILE = os.path.join(
        TRANSCRIPTS_DIR, f"meeting-{today}-{_session_counter}.txt"
    )
    _transcript_cache = []  # reset cache for new session
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Halo Transcript - Session {_session_counter} ({today})\n\n")
    return TRANSCRIPT_FILE


def _save_to_file(text: str):
    """Append a single line to the active transcript file."""
    if not TRANSCRIPT_FILE:
        _new_session_file()  # lazy init if not created yet
    with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def start_new_session():
    """Explicitly start a new transcript session."""
    return _new_session_file()


def record_continuous():
    """
    Start continuous recording and yield both partial + final transcripts.
    - Partials are yielded to UI only (not saved).
    - Finals are saved + cached + yielded to AI.
    """
    stream = start_stream()
    stream.start()

    try:
        for result in listen_continuous():
            if result["type"] == "final" and result["text"].strip():
                _transcript_cache.append(result["text"])
                _save_to_file(result["text"])
                yield {"type": "final", "text": result["text"]}
            elif result["type"] == "partial" and result["text"].strip():
                # only stream out, don't save or cache
                yield {"type": "partial", "text": result["text"]}
    finally:
        stop_streaming()
        stream.stop()
        stream.close()


def get_transcript_context():
    """
    Return the full transcript accumulated so far in this session.
    """
    return " ".join(_transcript_cache)
