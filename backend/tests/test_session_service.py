import sqlite3
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.db import connection as db_connection
from app.db.init_db import init_db
from app.repositories.profile_repository import ProfileRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import ProfileCreate
from app.schemas.session import (
    ParticipantCreate,
    ProfileActivation,
    SessionCreate,
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


@pytest.fixture
def session_database(monkeypatch, tmp_path):
    database_path = tmp_path / "data" / "sessions.sqlite3"
    monkeypatch.setattr(db_connection, "DATABASE_PATH", database_path)
    init_db()
    connection = sqlite3.connect(database_path)
    try:
        connection.executemany(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (?, ?, ?, ?)",
            [
                ("user-1", "User One", "one@example.invalid", "now"),
                ("user-2", "User Two", "two@example.invalid", "now"),
                ("user-3", "User Three", "three@example.invalid", "now"),
            ],
        )
        connection.commit()
    finally:
        connection.close()

    return database_path


@pytest.fixture
def session_service(session_database):
    return SessionService(
        repository=SessionRepository(),
        user_repository=UserRepository(),
        profile_repository=ProfileRepository(),
    )


def create_session(session_service, user_id="user-1"):
    return session_service.create_session(
        SessionCreate(created_by_user_id=user_id)
    )


def add_participant(
    session_service,
    session_id,
    user_id,
    role,
    profile_id=None,
):
    return session_service.add_participant(
        session_id=session_id,
        request=ParticipantCreate(
            user_id=user_id,
            role=role,
            profile_id=profile_id,
        ),
    )


def test_create_session(session_service):
    session = create_session(session_service)

    assert session.status == "active"
    assert session.created_by_user_id == "user-1"
    assert session.participants == []


def test_missing_creator_is_rejected(session_service):
    with pytest.raises(SessionUserNotFoundError):
        create_session(session_service, "missing-user")


def test_add_driver_and_passenger(session_service):
    session = create_session(session_service)

    driver = add_participant(session_service, session.session_id, "user-1", "driver")
    passenger = add_participant(session_service, session.session_id, "user-2", "passenger")

    assert driver.role == "driver"
    assert passenger.role == "passenger"


def test_multiple_passengers_are_allowed(session_service):
    session = create_session(session_service)

    add_participant(session_service, session.session_id, "user-2", "passenger")
    add_participant(session_service, session.session_id, "user-3", "passenger")

    assert len(session_service.get_session(session.session_id).participants) == 2


def test_second_driver_is_rejected(session_service):
    session = create_session(session_service)
    add_participant(session_service, session.session_id, "user-1", "driver")

    with pytest.raises(DriverAlreadyExistsError):
        add_participant(session_service, session.session_id, "user-2", "driver")


def test_duplicate_participant_is_rejected(session_service):
    session = create_session(session_service)
    add_participant(session_service, session.session_id, "user-1", "passenger")

    with pytest.raises(ParticipantAlreadyExistsError):
        add_participant(session_service, session.session_id, "user-1", "passenger")


def test_missing_participant_user_is_rejected(session_service):
    session = create_session(session_service)

    with pytest.raises(SessionUserNotFoundError):
        add_participant(session_service, session.session_id, "missing-user", "passenger")


def test_same_user_can_have_different_roles_in_different_sessions(session_service):
    driver_session = create_session(session_service)
    passenger_session = create_session(session_service, "user-2")

    driver = add_participant(session_service, driver_session.session_id, "user-1", "driver")
    passenger = add_participant(session_service, passenger_session.session_id, "user-1", "passenger")

    assert driver.role == "driver"
    assert passenger.role == "passenger"


def test_profile_ownership_is_required(session_service, session_database):
    profile_repository = ProfileRepository()
    profile = profile_repository.create_profile(
        profile_id="profile-1",
        user_id="user-2",
        profile_name="Other",
        is_default=True,
        driver_temperature=20,
        passenger_temperature=21,
        driver_seat_heating=0,
        passenger_seat_heating=0,
        fan_speed=2,
        volume=50,
        ambient_light="blue",
        created_at="now",
        updated_at="now",
    )
    session = create_session(session_service)

    with pytest.raises(ProfileNotOwnedError):
        add_participant(
            session_service,
            session.session_id,
            "user-1",
            "driver",
                profile["profile_id"],
        )


def test_profile_activation_requires_participant_and_ownership(
    session_service,
    session_database,
):
    profile_repository = ProfileRepository()
    profile_repository.create_profile(
        profile_id="profile-1",
        user_id="user-2",
        profile_name="Other",
        is_default=True,
        driver_temperature=20,
        passenger_temperature=21,
        driver_seat_heating=0,
        passenger_seat_heating=0,
        fan_speed=2,
        volume=50,
        ambient_light="blue",
        created_at="now",
        updated_at="now",
    )
    session = create_session(session_service)
    add_participant(session_service, session.session_id, "user-1", "driver")

    with pytest.raises(ProfileNotOwnedError):
        session_service.activate_profile(
            session_id=session.session_id,
            request=ProfileActivation(
                user_id="user-1",
                profile_id="profile-1",
            ),
        )

    with pytest.raises(ParticipantNotFoundError):
        session_service.activate_profile(
            session_id=session.session_id,
            request=ProfileActivation(
                user_id="user-2",
                profile_id="profile-1",
            ),
        )


def test_valid_profile_association(session_service, session_database):
    profile = ProfileRepository().create_profile(
        profile_id="profile-1",
        user_id="user-1",
        profile_name="Driver",
        is_default=True,
        driver_temperature=20,
        passenger_temperature=21,
        driver_seat_heating=0,
        passenger_seat_heating=0,
        fan_speed=2,
        volume=50,
        ambient_light="blue",
        created_at="now",
        updated_at="now",
    )
    session = create_session(session_service)
    add_participant(session_service, session.session_id, "user-1", "driver")

    participant = session_service.activate_profile(
        session_id=session.session_id,
        request=ProfileActivation(
            user_id="user-1",
                profile_id=profile["profile_id"],
        ),
    )

    assert participant.profile_id == profile["profile_id"]


def test_missing_session_is_rejected(session_service):
    with pytest.raises(SessionNotFoundError):
        session_service.get_session("missing-session")


def test_close_session(session_service):
    session = create_session(session_service)

    closed = session_service.close_session(session.session_id)

    assert closed.status == "inactive"


def test_inactive_session_cannot_be_modified(session_service):
    session = create_session(session_service)
    session_service.close_session(session.session_id)

    with pytest.raises(SessionInactiveError):
        add_participant(session_service, session.session_id, "user-1", "driver")

    with pytest.raises(SessionInactiveError):
        session_service.activate_profile(
            session_id=session.session_id,
            request=ProfileActivation(
                user_id="user-1",
                profile_id="profile-1",
            ),
        )


def test_session_is_returned_with_participants(session_service):
    session = create_session(session_service)
    add_participant(session_service, session.session_id, "user-1", "driver")
    add_participant(session_service, session.session_id, "user-2", "passenger")

    loaded = session_service.get_session(session.session_id)

    assert {participant.user_id for participant in loaded.participants} == {
        "user-1",
        "user-2",
    }


def test_profile_activation_does_not_touch_vehicle_state(
    session_service,
    session_database,
):
    profile = ProfileRepository().create_profile(
        profile_id="profile-1",
        user_id="user-1",
        profile_name="Driver",
        is_default=True,
        driver_temperature=20,
        passenger_temperature=21,
        driver_seat_heating=0,
        passenger_seat_heating=0,
        fan_speed=2,
        volume=50,
        ambient_light="blue",
        created_at="now",
        updated_at="now",
    )
    session = create_session(session_service)
    add_participant(session_service, session.session_id, "user-1", "driver")

    before = {
        "temperature": (20, 21),
        "volume": 50,
    }
    session_service.activate_profile(
        session_id=session.session_id,
        request=ProfileActivation(
            user_id="user-1",
                profile_id=profile["profile_id"],
        ),
    )

    assert before == {"temperature": (20, 21), "volume": 50}


def test_session_repository_closes_connections(session_database, monkeypatch):
    real_connection = db_connection.get_connection
    connections = []

    def tracked_connection():
        connection = real_connection()
        tracked = Mock(wraps=connection)
        connections.append(tracked)
        return tracked

    monkeypatch.setattr(
        "app.repositories.session_repository.get_connection",
        tracked_connection,
    )

    SessionRepository().get_by_id("missing-session")

    assert connections
    assert all(connection.close.called for connection in connections)


def test_foreign_keys_are_active(session_database):
    connection = db_connection.get_connection()
    try:
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        connection.close()

    assert foreign_keys == 1


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    database_path = tmp_path / "data" / "sessions-api.sqlite3"
    monkeypatch.setattr(db_connection, "DATABASE_PATH", database_path)

    from fastapi.dependencies import utils as dependency_utils

    monkeypatch.setattr(
        dependency_utils,
        "ensure_multipart_is_installed",
        lambda: None,
    )

    from app.main import app

    init_db()
    connection = sqlite3.connect(database_path)
    try:
        connection.executemany(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (?, ?, ?, ?)",
            [
                ("api-user", "API User", "api@example.invalid", "now"),
                ("api-passenger", "API Passenger", "passenger@example.invalid", "now"),
            ],
        )
        connection.commit()
    finally:
        connection.close()

    with TestClient(app) as client:
        yield client


def test_session_endpoints(api_client):
    create_response = api_client.post(
        "/sessions",
        json={"created_by_user_id": "api-user"},
    )
    session_id = create_response.json()["session_id"]
    participant_response = api_client.post(
        f"/sessions/{session_id}/participants",
        json={"user_id": "api-user", "role": "driver"},
    )
    get_response = api_client.get(f"/sessions/{session_id}")
    close_response = api_client.post(f"/sessions/{session_id}/close")

    assert create_response.status_code == 201
    assert participant_response.status_code == 201
    assert get_response.status_code == 200
    assert len(get_response.json()["participants"]) == 1
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "inactive"


def test_session_participants_are_persistent_and_roles_are_validated(api_client):
    session_id = api_client.post(
        "/sessions",
        json={"created_by_user_id": "api-user"},
    ).json()["session_id"]

    assert api_client.post(
        f"/sessions/{session_id}/participants",
        json={"user_id": "api-user", "role": "driver"},
    ).status_code == 201
    assert api_client.post(
        f"/sessions/{session_id}/participants",
        json={"user_id": "api-passenger", "role": "passenger"},
    ).status_code == 201
    assert api_client.post(
        f"/sessions/{session_id}/participants",
        json={"user_id": "api-passenger", "role": "passenger"},
    ).status_code == 409

    second_passenger = api_client.post(
        "/users",
        json={
            "name": "Second Passenger",
            "email": "second-passenger@example.invalid",
            "password": "secret123",
        },
    ).json()["user_id"]
    assert api_client.post(
        f"/sessions/{session_id}/participants",
        json={"user_id": second_passenger, "role": "passenger"},
    ).status_code == 201

    assert api_client.post(
        f"/sessions/{session_id}/participants",
        json={"user_id": second_passenger, "role": "driver"},
    ).status_code == 409
    assert api_client.put(
        f"/sessions/{session_id}/participants/{second_passenger}",
        json={"role": "driver"},
    ).status_code == 409

    assert api_client.delete(
        f"/sessions/{session_id}/participants/{second_passenger}"
    ).status_code == 204
    participants = api_client.get(f"/sessions/{session_id}").json()["participants"]
    assert {participant["user_id"] for participant in participants} == {
        "api-user",
        "api-passenger",
    }
