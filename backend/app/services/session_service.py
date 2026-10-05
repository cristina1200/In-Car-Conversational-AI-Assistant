import sqlite3
import uuid
from datetime import datetime, timezone

from app.repositories.profile_repository import ProfileRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.session import (
    ParticipantCreate,
    ParticipantResponse,
    ParticipantRoleUpdate,
    ProfileActivation,
    SessionCreate,
    SessionResponse,
)


class SessionNotFoundError(LookupError):
    pass


class SessionUserNotFoundError(LookupError):
    pass


class SessionInactiveError(ValueError):
    pass


class ParticipantAlreadyExistsError(ValueError):
    pass


class DriverAlreadyExistsError(ValueError):
    pass


class ParticipantNotFoundError(LookupError):
    pass


class ProfileNotOwnedError(ValueError):
    pass


class SessionService:
    def __init__(
        self,
        repository: SessionRepository | None = None,
        user_repository: UserRepository | None = None,
        profile_repository: ProfileRepository | None = None,
    ):
        self.repository = repository or SessionRepository()
        self.user_repository = user_repository or UserRepository()
        self.profile_repository = profile_repository or ProfileRepository()

    def create_session(self, request: SessionCreate) -> SessionResponse:
        self._require_user(request.created_by_user_id)
        row = self.repository.create_session(
            session_id=str(uuid.uuid4()),
            created_by_user_id=request.created_by_user_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return self._to_response(row, [])

    def add_participant(
        self,
        *,
        session_id: str,
        request: ParticipantCreate,
    ) -> ParticipantResponse:
        session = self._require_session(session_id)
        self._require_active(session)
        self._require_user(request.user_id)

        if self.repository.participant_exists(session_id, request.user_id):
            raise ParticipantAlreadyExistsError(
                "User is already a participant in this session"
            )

        if request.role == "driver" and self.repository.has_driver(session_id):
            raise DriverAlreadyExistsError(
                "Session already has a driver"
            )

        if request.profile_id is not None:
            self._require_owned_profile(
                request.profile_id,
                request.user_id,
            )

        try:
            row = self.repository.add_participant(
                session_id=session_id,
                user_id=request.user_id,
                role=request.role,
                profile_id=request.profile_id,
                joined_at=datetime.now(timezone.utc).isoformat(),
            )
        except sqlite3.IntegrityError as error:
            raise ParticipantAlreadyExistsError(
                "User is already a participant in this session"
            ) from error

        return self._to_participant_response(row)

    def get_session(self, session_id: str) -> SessionResponse:
        session = self._require_session(session_id)
        participants = self.repository.list_participants(session_id)
        return self._to_response(session, participants)

    def update_participant_role(
        self,
        *,
        session_id: str,
        user_id: str,
        request: ParticipantRoleUpdate,
    ) -> ParticipantResponse:
        session = self._require_session(session_id)
        self._require_active(session)
        self._require_user(user_id)

        participant = self.repository.get_participant(
            session_id=session_id,
            user_id=user_id,
        )
        if participant is None:
            raise ParticipantNotFoundError(
                "User is not a participant in this session"
            )

        if request.role == "driver":
            existing_driver = self.repository.has_driver(session_id)
            if existing_driver and participant["role"] != "driver":
                raise DriverAlreadyExistsError(
                    "Session already has a driver"
                )

        row = self.repository.update_participant_role(
            session_id=session_id,
            user_id=user_id,
            role=request.role,
        )
        if row is None:
            raise ParticipantNotFoundError(
                "User is not a participant in this session"
            )
        return self._to_participant_response(row)

    def remove_participant(
        self,
        *,
        session_id: str,
        user_id: str,
    ) -> None:
        session = self._require_session(session_id)
        self._require_active(session)
        self._require_user(user_id)
        if not self.repository.remove_participant(
            session_id=session_id,
            user_id=user_id,
        ):
            raise ParticipantNotFoundError(
                "User is not a participant in this session"
            )

    def activate_profile(
        self,
        *,
        session_id: str,
        request: ProfileActivation,
    ) -> ParticipantResponse:
        session = self._require_session(session_id)
        self._require_active(session)

        if not self.repository.participant_exists(
            session_id,
            request.user_id,
        ):
            raise ParticipantNotFoundError(
                "User is not a participant in this session"
            )

        self._require_owned_profile(request.profile_id, request.user_id)
        row = self.repository.associate_profile(
            session_id=session_id,
            user_id=request.user_id,
            profile_id=request.profile_id,
        )
        if row is None:
            raise ParticipantNotFoundError(
                "User is not a participant in this session"
            )

        return self._to_participant_response(row)

    def close_session(self, session_id: str) -> SessionResponse:
        session = self._require_session(session_id)
        self._require_active(session)
        row = self.repository.close_session(session_id)
        if row is None:
            raise SessionInactiveError("Session is already inactive")

        participants = self.repository.list_participants(session_id)
        return self._to_response(row, participants)

    def resolve_speaker(self, *, session_id: str, user_id: str) -> str:
        session = self._require_session(session_id)
        self._require_active(session)
        self._require_user(user_id)

        participant = self.repository.get_participant(
            session_id=session_id,
            user_id=user_id,
        )
        if participant is None:
            raise ParticipantNotFoundError(
                "User is not a participant in this session"
            )

        return participant["role"]

    def _require_session(self, session_id: str) -> sqlite3.Row:
        row = self.repository.get_by_id(session_id)
        if row is None:
            raise SessionNotFoundError("Session not found")
        return row

    def _require_user(self, user_id: str) -> None:
        if self.user_repository.get_by_id(user_id) is None:
            raise SessionUserNotFoundError("User not found")

    @staticmethod
    def _require_active(session: sqlite3.Row) -> None:
        if session["status"] != "active":
            raise SessionInactiveError("Session is inactive")

    def _require_owned_profile(self, profile_id: str, user_id: str) -> None:
        profile = self.profile_repository.get_by_id(profile_id)
        if profile is None or profile["user_id"] != user_id:
            raise ProfileNotOwnedError(
                "Profile does not belong to the user"
            )

    @staticmethod
    def _to_participant_response(row: sqlite3.Row) -> ParticipantResponse:
        return ParticipantResponse(
            session_id=row["session_id"],
            user_id=row["user_id"],
            role=row["role"],
            profile_id=row["profile_id"],
            joined_at=row["joined_at"],
        )

    @classmethod
    def _to_response(
        cls,
        row: sqlite3.Row,
        participants: list[sqlite3.Row],
    ) -> SessionResponse:
        return SessionResponse(
            session_id=row["session_id"],
            created_by_user_id=row["created_by_user_id"],
            status=row["status"],
            created_at=row["created_at"],
            participants=[
                cls._to_participant_response(participant)
                for participant in participants
            ],
        )
