FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg is required by openai-whisper to decode audio files.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install a CPU-only build of torch first so that openai-whisper does not
# pull in the multi-gigabyte CUDA wheels. Swap this for the CUDA index if
# you run this image on a machine with an NVIDIA GPU.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

EXPOSE 8082

CMD ["python", "app.py"]
