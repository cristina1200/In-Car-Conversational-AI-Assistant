import sqlite3
import uuid
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.db import connection as db_connection
from app.db.init_db import init_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.services.user_service import (
    DuplicateEmailError,
    InvalidCredentialsError,
    UserNotFoundError,
    UserService,
)


@pytest.fixture
def user_database(monkeypatch, tmp_path):
    database_path = tmp_path / "data" / "users.sqlite3"
    monkeypatch.setattr(db_connection, "DATABASE_PATH", database_path)
    init_db()
    return database_path


@pytest.fixture
def user_service(user_database):
    return UserService(UserRepository())


def make_user(email="test@example.invalid"):
    return UserCreate(
        name="Test User",
        email=email,
        password="test-password-123",
    )


def test_create_user(user_service):
    response = user_service.create_user(make_user())

    assert response.name == "Test User"
    assert response.email == "test@example.invalid"


def test_user_id_is_unique(user_service):
    first = user_service.create_user(make_user("one@example.invalid"))
    second = user_service.create_user(make_user("two@example.invalid"))

    assert first.user_id != second.user_id


def test_same_password_uses_unique_salts_and_is_not_returned(
    user_service,
    user_database,
):
    password = "same-password-123"
    first = user_service.create_user(
        UserCreate(
            name="First User",
            email="first@example.invalid",
            password=password,
        )
    )
    second = user_service.create_user(
        UserCreate(
            name="Second User",
            email="second@example.invalid",
            password=password,
        )
    )
    connection = sqlite3.connect(user_database)

    try:
        hashes = connection.execute(
            "SELECT password_hash FROM users WHERE user_id IN (?, ?) "
            "ORDER BY user_id",
            (first.user_id, second.user_id),
        ).fetchall()
    finally:
        connection.close()

    assert len(hashes) == 2
    assert hashes[0][0] != hashes[1][0]
    assert "password" not in first.model_dump()
    assert "password_hash" not in first.model_dump()
    assert "password" not in second.model_dump()
    assert "password_hash" not in second.model_dump()


def test_user_id_is_a_valid_uuid(user_service):
    response = user_service.create_user(make_user())

    parsed_user_id = uuid.UUID(response.user_id)

    assert str(parsed_user_id) == response.user_id


def test_duplicate_email_is_rejected(user_service):
    user_service.create_user(make_user())

    with pytest.raises(DuplicateEmailError):
        user_service.create_user(make_user())


def test_missing_user_is_rejected(user_service):
    with pytest.raises(UserNotFoundError):
        user_service.get_user("missing-user")


def test_login_returns_existing_user(user_service):
    created_user = user_service.create_user(make_user())

    logged_in_user = user_service.login(
        email="test@example.invalid",
        password="test-password-123",
    )

    assert logged_in_user.user_id == created_user.user_id
    assert logged_in_user.email == created_user.email


def test_login_rejects_wrong_password(user_service):
    user_service.create_user(make_user())

    with pytest.raises(InvalidCredentialsError):
        user_service.login(
            email="test@example.invalid",
            password="wrong-password",
        )


def test_password_is_not_returned_and_hash_is_not_plaintext(
    user_service,
    user_database,
):
    password = "test-password-123"
    response = user_service.create_user(
        UserCreate(
            name="Test User",
            email="hash@example.invalid",
            password=password,
        )
    )
    connection = sqlite3.connect(user_database)

    try:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE user_id = ?",
            (response.user_id,),
        ).fetchone()
    finally:
        connection.close()

    assert "password" not in response.model_dump()
    assert "password_hash" not in response.model_dump()
    assert row[0] != password
    assert row[0].startswith("scrypt$")


def test_user_defaults(user_service, user_database):
    response = user_service.create_user(make_user())
    connection = sqlite3.connect(user_database)

    try:
        row = connection.execute(
            "SELECT voice_enrolled, voice_embedding FROM users "
            "WHERE user_id = ?",
            (response.user_id,),
        ).fetchone()
    finally:
        connection.close()

    assert response.voice_enrolled is False
    assert row == (0, None)


def test_user_repository_closes_connections(user_database, monkeypatch):
    real_connection = db_connection.get_connection
    connections = []

    def tracked_connection():
        connection = real_connection()
        tracked = Mock(wraps=connection)
        connections.append(tracked)
        return tracked

    monkeypatch.setattr(
        "app.repositories.user_repository.get_connection",
        tracked_connection,
    )

    repository = UserRepository()
    repository.email_exists("none@example.invalid")

    assert connections
    assert all(connection.close.called for connection in connections)


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    database_path = tmp_path / "data" / "api.sqlite3"
    monkeypatch.setattr(db_connection, "DATABASE_PATH", database_path)

    from fastapi.dependencies import utils as dependency_utils

    monkeypatch.setattr(
        dependency_utils,
        "ensure_multipart_is_installed",
        lambda: None,
    )

    from app.main import app

    init_db()
    with TestClient(app) as client:
        yield client


def test_create_user_endpoint(api_client):
    response = api_client.post(
        "/users",
        json={
            "name": "API User",
            "email": "api@example.invalid",
            "password": "api-password-123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "api@example.invalid"
    assert "password" not in body
    assert "password_hash" not in body


def test_duplicate_email_endpoint_returns_conflict(api_client):
    payload = {
        "name": "API User",
        "email": "duplicate@example.invalid",
        "password": "api-password-123",
    }

    first_response = api_client.post("/users", json=payload)
    duplicate_response = api_client.post("/users", json=payload)

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


def test_get_user_endpoint(api_client):
    create_response = api_client.post(
        "/users",
        json={
            "name": "API User",
            "email": "api-get@example.invalid",
            "password": "api-password-123",
        },
    )
    user_id = create_response.json()["user_id"]

    response = api_client.get(f"/users/{user_id}")

    assert response.status_code == 200
    assert response.json()["user_id"] == user_id


def test_get_missing_user_endpoint(api_client):
    response = api_client.get("/users/missing-user")

    assert response.status_code == 404


def test_delete_user_endpoint_removes_account(api_client):
    create_response = api_client.post(
        "/users",
        json={
            "name": "Delete User",
            "email": "delete@example.invalid",
            "password": "delete-password-123",
        },
    )
    user_id = create_response.json()["user_id"]

    delete_response = api_client.delete(f"/users/{user_id}")

    assert delete_response.status_code == 204
    assert api_client.get(f"/users/{user_id}").status_code == 404


def test_delete_missing_user_endpoint_returns_not_found(api_client):
    response = api_client.delete("/users/missing-user")

    assert response.status_code == 404


def test_login_endpoint_returns_user(api_client):
    api_client.post(
        "/users",
        json={
            "name": "Login User",
            "email": "login@example.invalid",
            "password": "login-password-123",
        },
    )

    response = api_client.post(
        "/auth/login",
        json={
            "email": "LOGIN@EXAMPLE.INVALID",
            "password": "login-password-123",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "login@example.invalid"
    assert "password" not in response.json()


def test_login_endpoint_rejects_invalid_credentials(api_client):
    api_client.post(
        "/users",
        json={
            "name": "Login User",
            "email": "login-invalid@example.invalid",
            "password": "login-password-123",
        },
    )

    response = api_client.post(
        "/auth/login",
        json={
            "email": "login-invalid@example.invalid",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
