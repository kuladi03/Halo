import whisper
import torch
import numpy as np
from halo.utils.config_loader import config

DEVICE = "cuda" if (config.whisper.device == "cuda" and torch.cuda.is_available()) else "cpu"

print(f"Loading Whisper model ({config.whisper.model}) on {DEVICE}...")

whisper_model = whisper.load_model(config.whisper.model, device=DEVICE)

def transcribe_audio(audio_np: np.ndarray) -> str:
    """Transcribe raw audio (numpy array) into text using Whisper."""
    # Ensure float32, mono
    if audio_np.ndim > 1:
        audio_np = audio_np.mean(axis=1)  # convert to mono if stereo
    audio_np = audio_np.astype(np.float32)

    # Run Whisper directly on array
    result = whisper_model.transcribe(audio_np, fp16=(config.whisper.fp16 and DEVICE == "cuda"))
    return result["text"]
