import logging
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.ai.engine import process_message
from app.ai.speaker_recognition import SpeakerRecognitionService
from app.ai.transcription import transcribe_audio
from app.schemas.ai_response import VehicleAction
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.user_service import (
    DuplicateEmailError,
    InvalidCredentialsError,
    UserNotFoundError,
    UserService,
)
from app.repositories.user_repository import UserRepository
from app.db.init_db import init_db
from app.schemas.profile import (
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.session import (
    ParticipantCreate,
    ParticipantResponse,
    ParticipantRoleUpdate,
    ProfileActivation,
    SessionCreate,
    SessionResponse,
)
from app.services.profile_service import (
    ProfileNotFoundError,
    ProfileService,
    ProfileUserNotFoundError,
)
from app.services.session_service import (
    DriverAlreadyExistsError,
    ParticipantAlreadyExistsError,
    ParticipantNotFoundError,
    ProfileNotOwnedError,
    SessionInactiveError,
    SessionNotFoundError,
    SessionService,
    SessionUserNotFoundError,
)
from app.vehicle.constants import (
    AMBIENT_COLOR_LABELS_RO,
    AMBIENT_LIGHTS,
)
from app.vehicle.service import VehicleService
from app.vehicle.state import VehicleState

logger = logging.getLogger(__name__)

app = FastAPI(
    title="In-Car Conversational AI",
    description="Backend for the virtual vehicle simulator",
    version="0.1.0",
)


init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


vehicle_service = VehicleService()
user_service = UserService()
user_repository = UserRepository()
profile_service = ProfileService()
session_service = SessionService()
speaker_service = SpeakerRecognitionService()
chat_session_id = uuid4().hex


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantMessageRequest(BaseModel):
    message: str
    speaker: Literal["driver", "passenger"] | None = None
    input_type: Literal["text", "voice"] = "text"
    user_id: str | None = None
    session_id: str | None = None
    history: list[ConversationMessage] = Field(default_factory=list)
    action_history: list[VehicleAction] = Field(default_factory=list)


class VoiceEnrollmentResponse(BaseModel):
    user_id: str
    voice_enrolled: bool
    recordings: int


class VoiceEnrolledUserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    voice_enrolled: bool


class VoiceIdentifyResponse(BaseModel):
    matched: bool
    user_id: str | None = None
    user_name: str | None = None
    confidence: float = 0.0
    enrolled_users_count: int = 0
    rejection_reason: str | None = None
    role: Literal["driver", "passenger"] | None = None


class SpeakerResolveRequest(BaseModel):
    session_id: str
    user_id: str


class SpeakerResolveResponse(BaseModel):
    user_id: str
    session_id: str
    role: Literal["driver", "passenger"]


class AssistantMessageResponse(BaseModel):
    reply: str
    actions: list[VehicleAction]
    allowed: bool
    state: VehicleState
    session_id: str
    session_reset: bool


class AmbientLightOption(BaseModel):
    value: str
    label: str


class VehicleOptionsResponse(BaseModel):
    ambient_lights: list[AmbientLightOption]


@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(request: UserCreate):
    try:
        return user_service.create_user(request)
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@app.get(
    "/users/voice-enrolled",
    response_model=list[VoiceEnrolledUserResponse],
)
def list_voice_enrolled_users():
    return [
        VoiceEnrolledUserResponse(
            user_id=row["user_id"],
            name=row["name"],
            email=row["email"],
            voice_enrolled=bool(row["voice_enrolled"]),
        )
        for row in user_repository.list_voice_enrolled_users()
    ]


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    try:
        return user_service.get_user(user_id)
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: str):
    try:
        user_service.delete_user(user_id)
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@app.post("/auth/login", response_model=UserResponse)
def login_user(request: UserLogin):
    try:
        return user_service.login(
            email=request.email,
            password=request.password,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
        ) from error


@app.post("/profiles", response_model=ProfileResponse, status_code=201)
def create_profile(request: ProfileCreate):
    try:
        return profile_service.create_profile(request)
    except ProfileUserNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/profiles", response_model=list[ProfileResponse])
def list_profiles(user_id: str):
    try:
        return profile_service.list_profiles(user_id)
    except ProfileUserNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/profiles/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: str, user_id: str):
    try:
        return profile_service.get_profile(
            profile_id=profile_id,
            user_id=user_id,
        )
    except (ProfileNotFoundError, ProfileUserNotFoundError) as error:
        raise HTTPException(status_code=404, detail="Profile not found") from error


@app.put("/profiles/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: str,
    user_id: str,
    request: ProfileUpdate,
):
    try:
        return profile_service.update_profile(
            profile_id=profile_id,
            user_id=user_id,
            profile=request,
        )
    except (ProfileNotFoundError, ProfileUserNotFoundError) as error:
        raise HTTPException(status_code=404, detail="Profile not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(request: SessionCreate):
    try:
        return session_service.create_session(request)
    except SessionUserNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post(
    "/sessions/{session_id}/participants",
    response_model=ParticipantResponse,
    status_code=201,
)
def add_session_participant(
    session_id: str,
    request: ParticipantCreate,
):
    try:
        return session_service.add_participant(
            session_id=session_id,
            request=request,
        )
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SessionUserNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (SessionInactiveError, ParticipantAlreadyExistsError,
            DriverAlreadyExistsError, ProfileNotOwnedError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    try:
        return session_service.get_session(session_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.put(
    "/sessions/{session_id}/participants/{user_id}",
    response_model=ParticipantResponse,
)
def update_session_participant(
    session_id: str,
    user_id: str,
    request: ParticipantRoleUpdate,
):
    try:
        return session_service.update_participant_role(
            session_id=session_id,
            user_id=user_id,
            request=request,
        )
    except (SessionNotFoundError, SessionUserNotFoundError,
            ParticipantNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (SessionInactiveError, DriverAlreadyExistsError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.delete(
    "/sessions/{session_id}/participants/{user_id}",
    status_code=204,
)
def remove_session_participant(session_id: str, user_id: str):
    try:
        session_service.remove_participant(
            session_id=session_id,
            user_id=user_id,
        )
    except (SessionNotFoundError, SessionUserNotFoundError,
            ParticipantNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SessionInactiveError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post(
    "/sessions/{session_id}/profile",
    response_model=ParticipantResponse,
)
def activate_session_profile(
    session_id: str,
    request: ProfileActivation,
):
    try:
        return session_service.activate_profile(
            session_id=session_id,
            request=request,
        )
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ParticipantNotFoundError, ProfileNotOwnedError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SessionInactiveError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/sessions/{session_id}/close", response_model=SessionResponse)
def close_session(session_id: str):
    try:
        return session_service.close_session(session_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SessionInactiveError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Backend is running",
    }


@app.get("/vehicle/state", response_model=VehicleState)
def get_vehicle_state():
    return vehicle_service.get_state()


@app.get("/vehicle/options", response_model=VehicleOptionsResponse)
def get_vehicle_options():
    return {
        "ambient_lights": [
            {
                "value": color,
                "label": AMBIENT_COLOR_LABELS_RO[color],
            }
            for color in AMBIENT_LIGHTS
        ]
    }


@app.post("/vehicle/reset", response_model=VehicleState)
def reset_vehicle():
    return vehicle_service.reset()


@app.post(
    "/assistant/message",
    response_model=AssistantMessageResponse,
)
def process_assistant_message(
    request: AssistantMessageRequest,
):
    current_state = vehicle_service.get_state()
    is_same_chat_session = request.session_id == chat_session_id
    session_reset = request.session_id is not None and not is_same_chat_session

    resolved_speaker = request.speaker
    if request.input_type == "voice":
        if request.user_id and request.session_id:
            try:
                resolved_speaker = session_service.resolve_speaker(
                    session_id=request.session_id,
                    user_id=request.user_id,
                )
            except (
                SessionNotFoundError,
                SessionInactiveError,
                SessionUserNotFoundError,
                ParticipantNotFoundError,
            ):
                resolved_speaker = None

        logger.info(
            "Voice speaker resolution: session_id=%s identified_user_id=%s role=%s",
            request.session_id,
            request.user_id,
            resolved_speaker,
        )

    ai_response = process_message(
        message=request.message,
        speaker=resolved_speaker,
        conversation_history=[
            {"role": item.role, "content": item.content}
            for item in (request.history if is_same_chat_session else [])
        ],
        action_history=(
            request.action_history if is_same_chat_session else []
        ),
        current_temperature=current_state.temperature.driver,
        current_passenger_temperature=(
            current_state.temperature.passenger
        ),
        current_driver_seat_heating=(
            current_state.seat_heating.driver
        ),
        current_passenger_seat_heating=(
            current_state.seat_heating.passenger
        ),
        current_volume=current_state.volume,
        current_fan_speed=current_state.fan_speed,
        current_song=current_state.current_song,
        is_playing=current_state.is_playing,
        is_muted=current_state.is_muted,
        ambient_light=current_state.ambient_light,
        ac_enabled=current_state.ac_enabled,
    )

    if not ai_response.allowed:
        return {
            "reply": ai_response.reply,
            "actions": [],
            "allowed": False,
            "state": current_state,
            "session_id": chat_session_id,
            "session_reset": session_reset,
        }

    try:
        new_state = vehicle_service.execute_actions(
            ai_response.actions
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


    logger.info(
        "Assistant final actions: session_id=%s speaker=%s actions=%s",
        request.session_id,
        resolved_speaker,
        [action.model_dump() for action in ai_response.actions],
    )

    return {
        "reply": ai_response.reply,
        "actions": ai_response.actions,
        "allowed": ai_response.allowed,
        "state": new_state,
        "session_id": chat_session_id,
        "session_reset": session_reset,
    }


@app.post("/users/{user_id}/voice/enroll", response_model=VoiceEnrollmentResponse)
async def enroll_voice(
    user_id: str,
    files: list[UploadFile] = File(...),
):
    try:
        if not 3 <= len(files) <= 5:
            raise ValueError(
                "Trebuie să înregistrezi între 3 și 5 fragmente audio."
            )

        voice_data = [await uploaded_file.read() for uploaded_file in files]
        result = speaker_service.enroll_user(user_id, voice_data)
        return VoiceEnrollmentResponse(
            user_id=result["user_id"],
            voice_enrolled=result["voice_enrolled"],
            recordings=result["recordings"],
        )
    except UserNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/voice/identify", response_model=VoiceIdentifyResponse)
async def identify_voice(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
):
    try:
        audio_bytes = await file.read()
        result = speaker_service.identify_speaker(
            audio_bytes,
            session_id=session_id,
        )

        if result["matched"] and result["user_id"] and session_id:
            try:
                result["role"] = session_service.resolve_speaker(
                    session_id=session_id,
                    user_id=result["user_id"],
                )
            except (
                SessionNotFoundError,
                SessionInactiveError,
                SessionUserNotFoundError,
                ParticipantNotFoundError,
            ):
                result["role"] = None
        else:
            result["role"] = None

        logger.info(
            "Voice identification result: session_id=%s identified_user_id=%s "
            "matched=%s confidence=%s role=%s rejection_reason=%s",
            session_id,
            result.get("user_id"),
            result.get("matched"),
            result.get("confidence"),
            result.get("role"),
            result.get("rejection_reason"),
        )

        return VoiceIdentifyResponse(**result)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/voice/resolve-speaker", response_model=SpeakerResolveResponse)
def resolve_voice_speaker(request: SpeakerResolveRequest):
    try:
        role = session_service.resolve_speaker(
            session_id=request.session_id,
            user_id=request.user_id,
        )
    except (SessionNotFoundError, SessionInactiveError, ParticipantNotFoundError,
            SessionUserNotFoundError) as error:
        status_code = 404 if isinstance(error, (SessionNotFoundError, ParticipantNotFoundError, SessionUserNotFoundError)) else 409
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    return {
        "user_id": request.user_id,
        "session_id": request.session_id,
        "role": role,
    }


@app.post("/speech/transcribe")
async def transcribe_speech(
    file: UploadFile = File(...),
):
    try:
        text = await transcribe_audio(file)

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Transcrierea audio a eșuat.",
        ) from error

    return {
        "text": text,
    }
