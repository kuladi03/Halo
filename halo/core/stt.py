# halo/core/stt.py
import json
import vosk
from halo.utils.config_loader import config

# ===== CONFIG =====
TARGET_RATE = 16000  # Vosk always expects 16k mono PCM

# Load Vosk model (make sure you have the correct model downloaded)
MODEL_PATH = getattr(config.stt, "model_path", None)
vosk_model = vosk.Model(MODEL_PATH)


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe a block of audio bytes into text using Vosk.
    Use this for batch-style transcription of recorded audio.
    Input must already be 16kHz mono PCM.
    """
    recognizer = vosk.KaldiRecognizer(vosk_model, TARGET_RATE)

    if recognizer.AcceptWaveform(audio_bytes):
        result = json.loads(recognizer.Result())
        return result.get("text", "").strip()
    else:
        partial = json.loads(recognizer.PartialResult())
        return partial.get("partial", "").strip()


def transcribe_stream(recognizer, audio_bytes: bytes) -> dict:
    """
    Incremental transcription for continuous streaming.
    Returns either a partial or final result.
    Input must already be 16kHz mono PCM.
    """
    if recognizer.AcceptWaveform(audio_bytes):
        return {
            "type": "final",
            "text": json.loads(recognizer.Result()).get("text", "").strip(),
        }
    else:
        return {
            "type": "partial",
            "text": json.loads(recognizer.PartialResult()).get("partial", "").strip(),
        }
