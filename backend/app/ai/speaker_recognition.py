import io
import json
import logging
import math
import shutil
import subprocess
import wave
from typing import Sequence

from imageio_ffmpeg import get_ffmpeg_exe

from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserNotFoundError

VOICE_EMBEDDING_DIMENSION = 32
DEFAULT_CONFIDENCE_THRESHOLD = 0.50
MINIMUM_CONFIDENCE_MARGIN = 0.05
logger = logging.getLogger(__name__)


def _normalize(vector: Sequence[float]) -> list[float]:
    if not vector:
        return []

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return [float(value) for value in vector]

    return [float(value) / magnitude for value in vector]


def _extract_wav_vector(audio_bytes: bytes, size: int = VOICE_EMBEDDING_DIMENSION) -> list[float] | None:
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            sample_count = wav_file.getnframes()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            if sample_count <= 0 or sample_rate <= 0 or channels <= 0 or sample_width <= 0:
                return None

            raw_data = wav_file.readframes(sample_count)
    except (wave.Error, ValueError, OSError):
        return None

    if len(raw_data) == 0:
        return None

    sample_values: list[int] = []
    bytes_per_sample = sample_width
    for index in range(0, len(raw_data), bytes_per_sample):
        chunk = raw_data[index:index + bytes_per_sample]
        if len(chunk) < bytes_per_sample:
            break
        sample = int.from_bytes(chunk, byteorder="little", signed=True)
        sample_values.append(sample)

    if not sample_values:
        return None

    window_size = max(1, len(sample_values) // size)
    vector: list[float] = []

    for index in range(size):
        start = index * window_size
        end = start + window_size
        chunk = sample_values[start:end]
        if not chunk:
            vector.append(0.0)
            continue

        mean = sum(abs(value) for value in chunk) / len(chunk)
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        sign_changes = 0
        last_value = chunk[0]
        for value in chunk[1:]:
            if (last_value >= 0 and value < 0) or (last_value < 0 and value >= 0):
                sign_changes += 1
            last_value = value

        zero_ratio = sign_changes / max(1, len(chunk) - 1)
        amplitude = (mean / 32768.0) + (rms / 32768.0)
        mixed_feature = amplitude * 0.7 + (zero_ratio * 2.0 - 1.0) * 0.3
        vector.append(min(1.0, max(-1.0, mixed_feature)))

    return vector


def _get_ffmpeg_binary() -> str:
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        return ffmpeg_bin

    try:
        return get_ffmpeg_exe()
    except Exception as error:
        raise ValueError(
            "Audio decoding is unavailable: ffmpeg was not found in PATH "
            "or in the backend environment."
        ) from error


def _decode_to_pcm_wav(audio_bytes: bytes) -> bytes:
    if not audio_bytes:
        raise ValueError("Audio file is empty.")

    ffmpeg_bin = _get_ffmpeg_binary()

    try:
        process = subprocess.run(
            [
                ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-f",
                "wav",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-",
            ],
            input=audio_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        raise ValueError("Audio decoding failed while starting ffmpeg.") from None

    if process.returncode != 0 or not process.stdout:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            "Audio decoding failed; expected a supported WebM/Opus or WAV file."
            + (f" ffmpeg: {detail}" if detail else "")
        )

    try:
        with wave.open(io.BytesIO(process.stdout), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_count = wav_file.getnframes()
    except (wave.Error, ValueError, OSError) as error:
        raise ValueError("ffmpeg returned invalid PCM audio.") from error

    if sample_rate != 16000 or channels != 1 or sample_width != 2 or frame_count <= 0:
        raise ValueError("ffmpeg did not produce 16-bit, mono, 16 kHz PCM audio.")

    logger.info(
        "Decoded speaker audio: sample_rate=%s channels=%s sample_width=%s frames=%s",
        sample_rate,
        channels,
        sample_width,
        frame_count,
    )

    return process.stdout


def extract_embedding(audio_bytes: bytes) -> list[float]:
    sample_bytes = _decode_to_pcm_wav(audio_bytes)
    wav_vector = _extract_wav_vector(sample_bytes)
    if wav_vector is None:
        raise ValueError("Decoded audio did not contain usable PCM samples.")

    embedding = _normalize(wav_vector)
    logger.info("Generated speaker embedding: dimension=%s", len(embedding))
    return embedding


def average_embeddings(embeddings: Sequence[Sequence[float]]) -> list[float]:
    if not embeddings:
        return []

    dimension = len(embeddings[0])
    averages = [0.0 for _ in range(dimension)]

    for embedding in embeddings:
        if len(embedding) != dimension:
            continue
        for index, value in enumerate(embedding):
            averages[index] += float(value)

    for index in range(dimension):
        averages[index] /= len(embeddings)

    return _normalize(averages)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right:
        return 0.0

    if len(left) != len(right):
        common_length = min(len(left), len(right))
        left = left[:common_length]
        right = right[:common_length]

    dot_product = sum(a * b for a, b in zip(left, right))
    left_magnitude = math.sqrt(sum(a * a for a in left))
    right_magnitude = math.sqrt(sum(b * b for b in right))

    if left_magnitude == 0 or right_magnitude == 0:
        return 0.0

    return max(0.0, min(1.0, dot_product / (left_magnitude * right_magnitude)))


def serialize_embedding(embedding: Sequence[float]) -> bytes:
    return json.dumps([float(value) for value in embedding]).encode("utf-8")


def deserialize_embedding(raw: bytes | str | None) -> list[float]:
    if not raw:
        return []

    if isinstance(raw, bytes):
        raw_text = raw.decode("utf-8")
    else:
        raw_text = str(raw)

    try:
        payload = json.loads(raw_text)
    except (TypeError, ValueError):
        return []

    if not isinstance(payload, list):
        return []

    return [float(value) for value in payload]


class SpeakerRecognitionService:
    def __init__(
        self,
        user_repository: UserRepository | None = None,
        session_repository: SessionRepository | None = None,
    ):
        self.user_repository = user_repository or UserRepository()
        self.session_repository = session_repository or SessionRepository()

    def enroll_user(self, user_id: str, audio_files: Sequence[bytes]) -> dict:
        if self.user_repository.get_by_id(user_id) is None:
            raise UserNotFoundError("User not found")

        if not 3 <= len(audio_files) <= 5:
            raise ValueError("Trebuie să înregistrezi între 3 și 5 fragmente audio.")

        embeddings = [extract_embedding(audio) for audio in audio_files]
        representative = average_embeddings(embeddings)
        self.user_repository.save_voice_embedding(user_id, representative)
        logger.info(
            "Voice enrollment saved: user_id=%s recordings=%s embedding_dimension=%s "
            "mode=replaced",
            user_id,
            len(audio_files),
            len(representative),
        )

        return {
            "user_id": user_id,
            "voice_enrolled": True,
            "recordings": len(audio_files),
        }

    def identify_speaker(
        self,
        audio_bytes: bytes,
        session_id: str | None = None,
    ) -> dict:
        """Compare waveform-derived speaker embeddings, not the spoken text.

        Enrollment samples are treated as voice references only; the algorithm
        normalizes audio features into a compact embedding and measures cosine
        similarity. The message text is never inspected here, and Whisper stays
        separate for transcription.
        """
        if not audio_bytes:
            raise ValueError("Fișierul audio este gol.")

        candidate_embedding = extract_embedding(audio_bytes)
        if session_id:
            session = self.session_repository.get_by_id(session_id)
            if session is None or session["status"] != "active":
                enrolled_users = []
            else:
                enrolled_users = (
                    self.user_repository.list_voice_enrolled_users_for_session(
                        session_id
                    )
                )
        else:
            enrolled_users = []
        enrolled_users_count = len(enrolled_users)

        candidates: list[dict] = []

        for row in enrolled_users:
            saved_embedding = deserialize_embedding(row["voice_embedding"])
            if not saved_embedding:
                continue

            confidence = cosine_similarity(candidate_embedding, saved_embedding)
            logger.info(
                "Speaker similarity: user_id=%s confidence=%.4f threshold=%.2f",
                row["user_id"],
                confidence,
                DEFAULT_CONFIDENCE_THRESHOLD,
            )
            candidate = {
                "user_id": row["user_id"],
                "user_name": row["name"] if "name" in row.keys() else None,
                "confidence": confidence,
            }

            candidates.append(candidate)

        candidates.sort(key=lambda item: item["confidence"], reverse=True)

        if candidates:
            top_candidate = candidates[0]
            second_candidate = candidates[1] if len(candidates) > 1 else None
            score_margin = (
                top_candidate["confidence"] - second_candidate["confidence"]
                if second_candidate is not None
                else None
            )
            logger.info(
                "Speaker identification: session_id=%s identified_user_id=%s "
                "top_candidate=%s confidence=%.4f second_candidate=%s "
                "second_confidence=%s margin=%s threshold=%.2f",
                session_id,
                top_candidate["user_id"],
                top_candidate["user_id"],
                top_candidate["confidence"],
                second_candidate["user_id"] if second_candidate else None,
                f"{second_candidate['confidence']:.4f}"
                if second_candidate
                else None,
                f"{score_margin:.4f}" if score_margin is not None else None,
                DEFAULT_CONFIDENCE_THRESHOLD,
            )

        if not candidates:
            return {
                "matched": False,
                "user_id": None,
                "user_name": None,
                "confidence": 0.0,
                "role": None,
                "enrolled_users_count": enrolled_users_count,
                "rejection_reason": "No enrolled voice embedding matched among current session participants.",
            }

        best_match = candidates[0]
        second_match = candidates[1] if len(candidates) > 1 else None
        score_margin = (
            best_match["confidence"] - second_match["confidence"]
            if second_match is not None
            else None
        )

        if (
            second_match is not None
            and score_margin is not None
            and score_margin < MINIMUM_CONFIDENCE_MARGIN
        ):
            return {
                "matched": False,
                "user_id": None,
                "user_name": None,
                "confidence": round(float(best_match["confidence"]), 4),
                "role": None,
                "enrolled_users_count": enrolled_users_count,
                "rejection_reason": (
                    "Ambiguous voice match; the top two enrolled voices are "
                    f"within {MINIMUM_CONFIDENCE_MARGIN:.2f} similarity."
                ),
            }

        matched = best_match["confidence"] >= DEFAULT_CONFIDENCE_THRESHOLD
        if not matched:
            return {
                "matched": False,
                "user_id": None,
                "user_name": None,
                "confidence": round(float(best_match["confidence"]), 4),
                "role": None,
                "enrolled_users_count": enrolled_users_count,
                "rejection_reason": (
                    "Confidence below threshold; the audio did not match any enrolled voice strongly enough."
                ),
            }

        return {
            "matched": True,
            "user_id": best_match["user_id"],
            "user_name": best_match["user_name"],
            "confidence": round(float(best_match["confidence"]), 4),
            "role": None,
            "enrolled_users_count": enrolled_users_count,
            "rejection_reason": None,
        }
