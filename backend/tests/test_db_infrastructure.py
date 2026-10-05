import sqlite3
import subprocess
from pathlib import Path

import pytest

from app.db import connection as db_connection
from app.db.init_db import init_db


@pytest.fixture
def database_path(monkeypatch, tmp_path):
    database_path = tmp_path / "data" / "test.sqlite3"
    monkeypatch.setattr(db_connection, "DATABASE_PATH", database_path)
    return database_path


def test_database_is_created(database_path):
    assert not database_path.exists()

    init_db()

    assert database_path.is_file()


def test_required_tables_exist(database_path):
    init_db()
    connection = sqlite3.connect(database_path)

    try:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }
    finally:
        connection.close()

    assert {
        "users",
        "profiles",
        "sessions",
        "session_participants",
    }.issubset(table_names)


def test_connection_enables_foreign_keys_and_uses_rows(database_path):
    connection = db_connection.get_connection()

    try:
        foreign_keys_enabled = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]
        row_factory = connection.row_factory
    finally:
        connection.close()

    assert foreign_keys_enabled == 1
    assert row_factory is sqlite3.Row


def test_database_initialization_is_idempotent(database_path):
    init_db()
    init_db()
    connection = db_connection.get_connection()

    try:
        user_columns = connection.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    finally:
        connection.close()

    assert user_columns


def test_foreign_key_actions_are_configured(database_path):
    init_db()
    connection = sqlite3.connect(database_path)

    try:
        profile_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(profiles)"
        ).fetchall()
        participant_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(session_participants)"
        ).fetchall()
    finally:
        connection.close()

    assert any(
        row[2] == "users" and row[6] == "CASCADE"
        for row in profile_foreign_keys
    )
    assert any(
        row[2] == "sessions" and row[6] == "CASCADE"
        for row in participant_foreign_keys
    )
    assert any(
        row[2] == "users" and row[6] == "CASCADE"
        for row in participant_foreign_keys
    )
    assert any(
        row[2] == "profiles" and row[6] == "SET NULL"
        for row in participant_foreign_keys
    )


def test_profile_value_constraints_are_enforced(database_path):
    init_db()
    connection = db_connection.get_connection()

    try:
        connection.execute(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("user-1", "Test User", "test@example.invalid", "now"),
        )

        invalid_profiles = [
            ("driver_temperature", 15),
            ("passenger_temperature", 31),
            ("driver_seat_heating", 4),
            ("passenger_seat_heating", -1),
            ("fan_speed", 4),
            ("volume", 101),
            ("ambient_light", "orange"),
        ]

        for index, (column, value) in enumerate(invalid_profiles):
            values = {
                "profile_id": f"profile-{index}",
                "user_id": "user-1",
                "profile_name": "Test Profile",
                "driver_temperature": 20,
                "passenger_temperature": 21,
                "driver_seat_heating": 0,
                "passenger_seat_heating": 0,
                "fan_speed": 2,
                "volume": 50,
                "ambient_light": "blue",
                "created_at": "now",
                "updated_at": "now",
            }
            values[column] = value

            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO profiles ("
                    "profile_id, user_id, profile_name, "
                    "driver_temperature, passenger_temperature, "
                    "driver_seat_heating, passenger_seat_heating, "
                    "fan_speed, volume, ambient_light, created_at, updated_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    tuple(values.values()),
                )
    finally:
        connection.close()


def test_session_status_and_participant_role_constraints_are_enforced(
    database_path,
):
    init_db()
    connection = db_connection.get_connection()

    try:
        connection.execute(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("user-1", "Test User", "test@example.invalid", "now"),
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO sessions "
                "(session_id, created_by_user_id, status, created_at) "
                "VALUES (?, ?, ?, ?)",
                ("session-1", "user-1", "paused", "now"),
            )

        connection.execute(
            "INSERT INTO sessions "
            "(session_id, created_by_user_id, status, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("session-1", "user-1", "active", "now"),
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO session_participants "
                "(session_id, user_id, role, joined_at) "
                "VALUES (?, ?, ?, ?)",
                ("session-1", "user-1", "observer", "now"),
            )
    finally:
        connection.close()


def test_database_file_is_ignored_by_git():
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "backend/data/app.sqlite3"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
