from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SessionStatus = Literal["active", "inactive"]
ParticipantRole = Literal["driver", "passenger"]


class SessionCreate(BaseModel):
    created_by_user_id: str = Field(min_length=1)


class ParticipantCreate(BaseModel):
    user_id: str = Field(min_length=1)
    role: ParticipantRole
    profile_id: str | None = None


class ParticipantRoleUpdate(BaseModel):
    role: ParticipantRole


class ProfileActivation(BaseModel):
    user_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)


class ParticipantResponse(BaseModel):
    session_id: str
    user_id: str
    role: ParticipantRole
    profile_id: str | None
    joined_at: str


class SessionResponse(BaseModel):
    session_id: str
    created_by_user_id: str
    status: SessionStatus
    created_at: str
    participants: list[ParticipantResponse]
