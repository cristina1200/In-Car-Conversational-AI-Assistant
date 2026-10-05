import sqlite3
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.db import connection as db_connection
from app.db.init_db import init_db
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileCreate, ProfileUpdate
from app.services.profile_service import (
    ProfileNotFoundError,
    ProfileService,
    ProfileUserNotFoundError,
)


@pytest.fixture
def profile_database(monkeypatch, tmp_path):
    database_path = tmp_path / "data" / "profiles.sqlite3"
    monkeypatch.setattr(db_connection, "DATABASE_PATH", database_path)
    init_db()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("user-1", "Test User", "test@example.invalid", "now"),
        )
        connection.execute(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("user-2", "Other User", "other@example.invalid", "now"),
        )
        connection.commit()
    finally:
        connection.close()

    return database_path


@pytest.fixture
def profile_service(profile_database):
    return ProfileService(ProfileRepository())


def make_profile(user_id="user-1", **overrides):
    values = {
        "user_id": user_id,
        "profile_name": "Comfort",
    }
    values.update(overrides)
    return ProfileCreate(**values)


def test_create_profile(profile_service):
    profile = profile_service.create_profile(make_profile())

    assert profile.user_id == "user-1"
    assert profile.profile_name == "Comfort"
    assert profile.is_default is True
    assert profile.driver_temperature == profile.passenger_temperature
    assert profile.driver_seat_heating == profile.passenger_seat_heating


def test_list_profiles_is_scoped_to_user(profile_service):
    profile_service.create_profile(make_profile(profile_name="Driver"))
    profile_service.create_profile(
        make_profile("user-2", profile_name="Other")
    )

    profiles = profile_service.list_profiles("user-1")

    assert len(profiles) == 1
    assert profiles[0].user_id == "user-1"


def test_get_profile(profile_service):
    created = profile_service.create_profile(make_profile())

    profile = profile_service.get_profile(
        profile_id=created.profile_id,
        user_id="user-1",
    )

    assert profile.profile_id == created.profile_id


def test_update_profile(profile_service):
    created = profile_service.create_profile(make_profile())

    updated = profile_service.update_profile(
        profile_id=created.profile_id,
        user_id="user-1",
        profile=ProfileUpdate(volume=80, ambient_light="purple"),
    )

    assert updated.volume == 80
    assert updated.ambient_light == "purple"
    assert updated.profile_name == "Comfort"


def test_updating_one_zone_preference_updates_both_zones(profile_service):
    created = profile_service.create_profile(make_profile())

    updated = profile_service.update_profile(
        profile_id=created.profile_id,
        user_id="user-1",
        profile=ProfileUpdate(
            passenger_temperature=26,
            passenger_seat_heating=2,
        ),
    )

    assert updated.driver_temperature == 26
    assert updated.passenger_temperature == 26
    assert updated.driver_seat_heating == 2
    assert updated.passenger_seat_heating == 2


def test_unknown_user_is_rejected(profile_service):
    with pytest.raises(ProfileUserNotFoundError):
        profile_service.create_profile(make_profile("missing-user"))


def test_unknown_profile_is_rejected(profile_service):
    with pytest.raises(ProfileNotFoundError):
        profile_service.get_profile(
            profile_id="missing-profile",
            user_id="user-1",
        )


def test_profile_of_another_user_is_not_accessible(profile_service):
    created = profile_service.create_profile(make_profile("user-2"))

    with pytest.raises(ProfileNotFoundError):
        profile_service.get_profile(
            profile_id=created.profile_id,
            user_id="user-1",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("driver_temperature", 15),
        ("passenger_temperature", 31),
        ("driver_seat_heating", 4),
        ("passenger_seat_heating", -1),
        ("fan_speed", 4),
        ("volume", 101),
        ("ambient_light", "orange"),
    ],
)
def test_invalid_profile_values_are_rejected(
    profile_service,
    field,
    value,
):
    with pytest.raises(ValueError):
        profile_service.create_profile(make_profile(**{field: value}))


def test_only_one_profile_is_default(profile_service):
    first = profile_service.create_profile(make_profile())
    second = profile_service.create_profile(
        make_profile(profile_name="Sport", is_default=True)
    )

    profiles = profile_service.list_profiles("user-1")

    assert first.is_default is True
    assert second.is_default is True
    assert sum(profile.is_default for profile in profiles) == 1
    assert next(profile for profile in profiles if profile.is_default).profile_id == second.profile_id


def test_profile_defaults_are_independent_between_users(profile_service):
    first = profile_service.create_profile(make_profile())
    second = profile_service.create_profile(
        make_profile("user-2", profile_name="Other")
    )

    assert first.is_default is True
    assert second.is_default is True


def test_repository_closes_connections(profile_database, monkeypatch):
    real_connection = db_connection.get_connection
    connections = []

    def tracked_connection():
        connection = real_connection()
        tracked = Mock(wraps=connection)
        connections.append(tracked)
        return tracked

    monkeypatch.setattr(
        "app.repositories.profile_repository.get_connection",
        tracked_connection,
    )

    ProfileRepository().user_exists("user-1")

    assert connections
    assert all(connection.close.called for connection in connections)


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    database_path = tmp_path / "data" / "profiles-api.sqlite3"
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
        connection.execute(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("api-user", "API User", "api@example.invalid", "now"),
        )
        connection.execute(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("other-user", "Other User", "other@example.invalid", "now"),
        )
        connection.commit()
    finally:
        connection.close()

    with TestClient(app) as client:
        yield client


def test_profile_endpoints(api_client):
    create_response = api_client.post(
        "/profiles",
        json={
            "user_id": "api-user",
            "profile_name": "API Profile",
        },
    )
    profile_id = create_response.json()["profile_id"]

    assert create_response.status_code == 201

    list_response = api_client.get(
        "/profiles",
        params={"user_id": "api-user"},
    )
    get_response = api_client.get(
        f"/profiles/{profile_id}",
        params={"user_id": "api-user"},
    )
    update_response = api_client.put(
        f"/profiles/{profile_id}",
        params={"user_id": "api-user"},
        json={"volume": 75},
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["volume"] == 75


def test_profile_endpoints_reject_invalid_ownership_and_missing_users(
    api_client,
):
    create_response = api_client.post(
        "/profiles",
        json={
            "user_id": "api-user",
            "profile_name": "API Profile",
        },
    )
    profile_id = create_response.json()["profile_id"]

    foreign_response = api_client.get(
        f"/profiles/{profile_id}",
        params={"user_id": "other-user"},
    )
    missing_user_response = api_client.get(
        "/profiles",
        params={"user_id": "missing-user"},
    )

    assert foreign_response.status_code == 404
    assert missing_user_response.status_code == 404


def test_put_profile_rejects_other_user_and_preserves_profile(api_client):
    create_response = api_client.post(
        "/profiles",
        json={
            "user_id": "api-user",
            "profile_name": "Protected Profile",
            "volume": 40,
        },
    )
    profile_id = create_response.json()["profile_id"]

    update_response = api_client.put(
        f"/profiles/{profile_id}",
        params={"user_id": "other-user"},
        json={"volume": 99},
    )
    read_response = api_client.get(
        f"/profiles/{profile_id}",
        params={"user_id": "api-user"},
    )

    assert update_response.status_code == 404
    assert read_response.status_code == 200
    assert read_response.json()["volume"] == 40
