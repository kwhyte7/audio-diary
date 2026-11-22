import os

import torch
import whisper

from settings import settings

_model = None
_device = None


def get_model():
    """Load the Whisper model once and reuse it for later transcriptions."""
    global _model, _device
    if _model is not None:
        return _model

    cfg = settings["transcribe"]["whisper"]
    model_name = cfg.get("model_size_or_path", "small")
    device = cfg.get("device", "auto") or "auto"

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    elif device == "cuda" and not torch.cuda.is_available():
        print("[whisper] CUDA requested but not available, falling back to CPU")
        device = "cpu"

    download_root = os.getenv("WHISPER_DOWNLOAD_ROOT") or None

    print(f"[whisper] loading model '{model_name}' on {device}")
    _device = device
    _model = whisper.load_model(model_name, device=device, download_root=download_root)
    return _model


def transcribe(audio_path):
    model = get_model()
    # Half precision is faster (and needs less VRAM) on GPU; on CPU stick to fp32.
    result = model.transcribe(audio_path, fp16=(_device == "cuda"))
    return result["text"].strip()


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "./input.wav"
    print(transcribe(path))
