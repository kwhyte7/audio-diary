# Audio Diary

A small, self-hosted dictation app. You talk, Whisper turns your speech into
text, and the words land straight in a Quill document you can edit and save.

Images:

![Sign up](imgs/signup.jpg)
![Overview](imgs/documents_overview.jpg)
![Editor](imgs/editor.jpg)
![Create Document](imgs/create_document.jpg)

## What changed

- Nicer login and sign-up pages.
- Storage moved from JSON files to **PostgreSQL** (users, sessions and document
  contents). Raw audio recordings still live on the filesystem under `data/`
  because they're binary blobs.
- A `docker-compose.yml` that runs the app **and** Postgres together.
- Whisper setup notes, because it needs a bit more than a `pip install`.

## The quickest way: Docker

```bash
cp .env.example .env   # optional: change ports / password / secret key
docker compose up --build
```

Then open <http://localhost:8082>. That's it. The compose file spins up Postgres
and the app, and mounts volumes for the database, uploaded audio and the
Whisper model cache.

You don't have to touch `docker-compose.yml`. Copy `.env.example` to `.env` and
tweak `APP_PORT`, `DATABASE_URL`, `POSTGRES_PORT`, `POSTGRES_PASSWORD`,
`SECRET_KEY`, etc. `docker compose` reads that `.env` automatically.

### Using an existing Postgres on your host

If you already run Postgres on your machine, you can point the app at it and
move the bundled one out of the way, all in `.env`:

```bash
# Use your own database instead of the bundled one:
DATABASE_URL=postgresql://user:password@host.docker.internal:5432/audio_diary

# Free up host port 5432 (your own Postgres is using it):
POSTGRES_PORT=5433
```

`host.docker.internal` reaches the host from inside a container (on Linux you
may need `extra_hosts` or the gateway IP `172.17.0.1` instead). If you don't
need the bundled Postgres at all, just comment out the `db` service in
`docker-compose.yml` and remove the `depends_on` block.

> The Docker image uses a **CPU** build of torch to keep the image size sane.
> CPU transcription works fine for `tiny`/`base`/`small`; it just isn't fast.

## Running it by hand

You need Python 3.12, `ffmpeg`, and a Postgres database. `ffmpeg` is a hard
requirement for Whisper — it decodes the audio before the model sees it.

**macOS:**

```bash
brew install ffmpeg
```

**Debian / Ubuntu:**

```bash
sudo apt install ffmpeg
```

**Postgres:** you can run just the database with Docker and run the app on your
host if you prefer:

```bash
docker compose up -d db
```

Then create the database (the compose file already does this, but if you're
pointing at your own Postgres):

```sql
CREATE DATABASE audio_diary;
```

Install the Python deps with `uv`:

```bash
uv sync
```

If `uv` says the lockfile is out of date (it can happen after dependency
changes), refresh it first:

```bash
uv lock
uv sync
```

Set the connection string and run the app:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/audio_diary"
export SECRET_KEY="some-long-random-string"
uv run app.py
```

Open <http://localhost:8082>.

## What Whisper needs

Whisper has three real requirements beyond the Python packages:

1. **ffmpeg** — must be on your `PATH`. Without it Whisper raises an
   `FileNotFoundError` when you try to transcribe.
2. **PyTorch** — installed automatically as a dependency, but the *flavour*
   matters. On Linux the default PyPI wheel ships with CUDA libraries and is
   several gigabytes. If you don't have an NVIDIA GPU, install the CPU build:

   ```bash
   uv pip install torch --index-url https://download.pytorch.org/whl/cpu
   uv sync
   ```

3. **The model weights** — downloaded the first time you transcribe. They go to
   `~/.cache/whisper` (or `WHISPER_DOWNLOAD_ROOT` if you set it). The model size
   is picked in `settings.yml`:

   | Model  | Approx. size | RAM needed  | Notes                        |
   | ------ | ------------ | ----------- | ---------------------------- |
   | tiny   | ~75 MB       | ~1 GB       | Fast, rough                  |
   | base   | ~145 MB      | ~1 GB       | Fast-ish                     |
   | small  | ~484 MB      | ~2 GB       | Good default (current)       |
   | medium | ~1.5 GB      | ~5 GB       | Better, slower               |
   | large  | ~3 GB        | ~10 GB      | Best quality, slowest        |
   | turbo  | ~1.6 GB      | ~6 GB       | large-quality, faster        |

   To change it, edit `settings.yml`:

   ```yaml
   transcribe:
     whisper:
       model_size_or_path: small   # tiny / base / small / medium / large / turbo
       device: auto                # auto, cpu, or cuda
   ```

## GPU notes (optional)

If you have an NVIDIA GPU and CUDA set up, set `device: cuda` in `settings.yml`
(or leave it on `auto` and it'll pick CUDA when available). Local `uv sync`
installs the CUDA build of torch; the Docker image does **not**, to keep it
portable. Want GPU in Docker? Swap the CPU torch line in the `Dockerfile` for:

```dockerfile
RUN pip install --no-cache-dir torch
```

and make sure the container has access to your GPU runtime.

## Project layout

- `app.py` — Flask app and routes.
- `db.py` — Postgres access (users, sessions, documents).
- `transcribe.py` — Whisper model loading and transcription.
- `settings.yml` — model choice and transcription settings.
- `templates/`, `static/` — the web UI.
- `data/` — per-user audio recordings (created at runtime).
