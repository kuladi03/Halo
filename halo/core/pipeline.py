import torch
from halo.core.listener import record_until_silence
from halo.core.stt import transcribe_audio
from halo.core.llm import query_ollama

# ----------------- Transcript Cache -----------------
_transcript_cache = []

def record_continuous():
    """
    Record speech until silence, transcribe it, 
    and store in the global transcript cache.
    Returns the transcribed text.
    """
    audio = record_until_silence()
    text = transcribe_audio(audio)
    if text.strip():
        _transcript_cache.append(text)
    return text

def get_transcript_context():
    """
    Return the full transcript accumulated so far.
    """
    return " ".join(_transcript_cache)

# ----------------- Legacy CLI loop -----------------
def run_once():
    """Run a single Halo cycle: Listen → STT → LLM → Reply"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Running one Halo cycle on {device}")

    # Step 1: Listen until silence
    audio = record_until_silence()

    # Step 2: Transcribe with Whisper
    text = transcribe_audio(audio)
    print(f"📝 You said: {text}")

    if not text.strip():
        print("❌ No speech detected, try again...")
        return {"text": "", "reply": ""}

    # Step 3: Query Ollama
    print("🤖 Thinking...")
    reply = query_ollama(text)
    print(f"💡 Halo: {reply}")

    return {"text": text, "reply": reply}

def run():
    """Legacy CLI loop: Keeps running until user says 'exit' or 'quit'"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Starting Halo (running on {device})")

    while True:
        result = run_once()
        text, reply = result["text"], result["reply"]

        # Exit condition
        if "exit" in text.lower() or "quit" in text.lower():
            print("👋 Goodbye from Halo!")
            break
