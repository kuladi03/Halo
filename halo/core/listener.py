# lsitener.py

import queue
import sounddevice as sd
import numpy as np
import torch
import torchaudio
from silero_vad import load_silero_vad, get_speech_timestamps

# ===== CONFIG =====
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1024

# Load Silero VAD model properly
vad_model = load_silero_vad(onnx=False)  # torch model (onnx=True if you prefer ONNX)

def record_until_silence():
    """Continuously record until silence is detected using Silero VAD"""
    print("🎙 Listening... (speak and pause to stop)")

    audio_buffer = []
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        blocksize=BLOCK_SIZE,
        dtype="float32"
    )
    stream.start()

    while True:
        block, _ = stream.read(BLOCK_SIZE)
        if block is None:
            continue

        audio_buffer.append(block)
        audio_np = np.concatenate(audio_buffer, axis=0)

        # Convert numpy → torch
        audio_tensor = torch.from_numpy(audio_np).float().squeeze()
        if audio_tensor.ndim == 1:
            audio_tensor = audio_tensor.unsqueeze(0)

        # Run VAD
        speech_timestamps = get_speech_timestamps(
            audio_tensor, vad_model,
            sampling_rate=SAMPLE_RATE
        )

        if len(speech_timestamps) > 0:
            last_speech = speech_timestamps[-1]
            # Stop if silence > 0.8s
            if last_speech["end"] < audio_tensor.shape[1] - int(SAMPLE_RATE * 0.8):
                break

    stream.stop()
    print("✅ Speech segment captured")
    return np.concatenate(audio_buffer, axis=0)
