# Audio dictation document editor

Images:
![Sign up](imgs/signup.jpg)
![Overview](imgs/documents_overview.jpg)
![Editor](imgs/editor.jpg)
![Create Document](imgs/create_document.jpg)

Open source, simple dictation software, that uses OpenAI's whisper to allow you to dictate a document, transcribing your words from speech to text.
Uses Quill for the editor

Installation instructions:
Use:
```bash
uv sync
```
in order to install the dependencies. 

Use:
```bash
uv run app.py
```
To run the application.

You can run it using docker aswell, by using:
```bash
docker compose up
```
To run the application on port 8082.

