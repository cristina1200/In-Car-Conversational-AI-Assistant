import os

from fastapi import UploadFile
from openai import OpenAI

from app.ai.engine import get_client
from app.vehicle.constants import MAX_AUDIO_BYTES


async def transcribe_audio(file: UploadFile) -> str:
    client: OpenAI | None = get_client()

    if client is None:
        raise RuntimeError("Cheia OpenAI nu a fost găsită.")

    model = os.getenv("OPENAI_TRANSCRIPTION_MODEL")

    if not model:
        raise RuntimeError(
            "Modelul pentru transcriere nu este configurat."
        )

    audio_bytes = await file.read()

    if not audio_bytes:
        raise ValueError("Fișierul audio este gol.")

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError("Fișierul audio este prea mare.")

    filename = file.filename or "speech.webm"
    content_type = file.content_type or "audio/webm"

    response = client.audio.transcriptions.create(
        model=model,
        file=(filename, audio_bytes, content_type),
    )

    return response.text.strip()
