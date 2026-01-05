import yaml
#from faster_whisper import WhisperModel # faster-whisper isn't working at the moment, while i don't have cunting libcublas 12
import whisper
from settings import settings

""" Using faster-whisper
model = WhisperModel(**settings["transcribe"]["whisper"]) 
def transcribe(audio_path):
    print(audio_path)
    segments, info = model.transcribe(audio_path, beam_size=settings["transcribe"]["beam_size"])
    content = ""

    for segment in segments:
        content = content + f"{segment.text}"

    return content.strip()
"""

model = whisper.load_model(settings["transcribe"]["whisper"]["model_size_or_path"])
def transcribe(audio_path):

    result = model.transcribe(audio_path, fp16=False)
    return result["text"]

if __name__ == "__main__":
    print(transcribe("./input.wav"))
