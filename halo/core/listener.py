# halo/core/listener.py

import queue
import sounddevice as sd
import numpy as np
import vosk
import json

# ===== CONFIG =====
MIC_RATE = 48000       # native mic rate (your laptop mic)
TARGET_RATE = 16000    # what Vosk expects
CHANNELS = 2           # mic is stereo (2 channels)
BLOCK_SIZE = 8192     # or use  16384  

# Queue for streaming audio
audio_queue = queue.Queue()

# Initialize Vosk model
MODEL_PATH = r"C:\Users\Hari\AppData\Local\vosk-model-en-in-0.5"
vosk_model = vosk.Model(MODEL_PATH)
recognizer = vosk.KaldiRecognizer(vosk_model, TARGET_RATE)

# Flag for stopping listener
stop_listening = False


# ------------------ Helpers ------------------

def resample_and_downmix(data: bytes, samplerate: int, target_rate: int) -> bytes:
    """
    Convert stereo float32 → mono int16 PCM at target_rate (for Vosk).
    """
    audio = np.frombuffer(data, dtype=np.float32)

    # Reshape into [N, channels]
    audio = audio.reshape(-1, CHANNELS)

    # Downmix: average L+R channels
    mono = audio.mean(axis=1)

    # Normalize amplitude to [-1, 1]
    max_val = np.max(np.abs(mono))
    if max_val > 0:
        mono = mono / max_val

    # Resample from samplerate → target_rate
    ratio = target_rate / samplerate
    new_len = int(len(mono) * ratio)
    resampled = np.interp(
        np.linspace(0, len(mono), new_len),
        np.arange(len(mono)),
        mono
    )

    # Convert to 16-bit PCM bytes
    return (resampled * 32767).astype(np.int16).tobytes()


def audio_callback(indata, frames, time, status):
    """
    Called automatically when new audio is available.
    Converts audio and pushes it into the queue.
    """
    if status:
        print(f"[Audio Warning] {status}")

    audio_bytes = resample_and_downmix(indata.tobytes(), MIC_RATE, TARGET_RATE)
    audio_queue.put(audio_bytes)


# ------------------ Main API ------------------

def start_stream():
    """
    Starts the microphone stream and returns the InputStream.
    """
    return sd.InputStream(
        samplerate=MIC_RATE,
        channels=CHANNELS,
        blocksize=BLOCK_SIZE,
        dtype="float32",
        callback=audio_callback
    )


def listen_continuous():
    """
    Generator that yields dicts with type + text.
    Example:
        {"type": "partial", "text": "hel"}
        {"type": "final", "text": "hello world"}
    """
    global stop_listening
    while not stop_listening:
        if not audio_queue.empty():
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    yield {"type": "final", "text": text}
            else:
                partial = json.loads(recognizer.PartialResult())
                text = partial.get("partial", "").strip()
                if text:
                    yield {"type": "partial", "text": text}
        else:
            sd.sleep(10)  # small sleep to avoid busy waiting


def stop_streaming():
    """
    Stops the listening loop.
    """
    global stop_listening
    stop_listening = True
