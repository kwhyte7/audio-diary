import yaml
from faster_whisper import WhisperModel
from settings import settings

model = WhisperModel(**settings["transcribe"]["whisper"]) 
def transcribe(audio_path):
    segments, info = model.transcribe(audio_path, beam_size=settings["transcribe"]["beam_size"])
    content = ""

    for segment in segments:
        content = content + f"{segment.text}"

    return content

if __name__ == "__main__":
    print(transcribe("./input.wav"))
