from .connection import get_connection
from app.vehicle.constants import (
    AMBIENT_LIGHTS,
    DEFAULT_AMBIENT_LIGHT,
    DEFAULT_DRIVER_TEMPERATURE,
    DEFAULT_DRIVER_SEAT_HEATING,
    DEFAULT_FAN_SPEED,
    DEFAULT_PASSENGER_TEMPERATURE,
    DEFAULT_PASSENGER_SEAT_HEATING,
    DEFAULT_VOLUME,
    MAX_FAN_SPEED,
    MAX_SEAT_HEATING,
    MAX_TEMPERATURE,
    MAX_VOLUME,
    MIN_FAN_SPEED,
    MIN_SEAT_HEATING,
    MIN_TEMPERATURE,
    MIN_VOLUME,
)


AMBIENT_LIGHT_SQL_VALUES = ", ".join(
    f"'{color}'" for color in AMBIENT_LIGHTS
)


SCHEMA = f"""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NULL,
    voice_enrolled INTEGER NOT NULL DEFAULT 0,
    voice_embedding BLOB NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
    profile_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    profile_name TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    driver_temperature INTEGER NOT NULL DEFAULT {DEFAULT_DRIVER_TEMPERATURE},
    passenger_temperature INTEGER NOT NULL DEFAULT {DEFAULT_PASSENGER_TEMPERATURE},
    driver_seat_heating INTEGER NOT NULL DEFAULT {DEFAULT_DRIVER_SEAT_HEATING},
    passenger_seat_heating INTEGER NOT NULL DEFAULT {DEFAULT_PASSENGER_SEAT_HEATING},
    fan_speed INTEGER NOT NULL DEFAULT {DEFAULT_FAN_SPEED},
    volume INTEGER NOT NULL DEFAULT {DEFAULT_VOLUME},
    ambient_light TEXT NOT NULL DEFAULT '{DEFAULT_AMBIENT_LIGHT}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (driver_temperature BETWEEN {MIN_TEMPERATURE} AND {MAX_TEMPERATURE}),
    CHECK (passenger_temperature BETWEEN {MIN_TEMPERATURE} AND {MAX_TEMPERATURE}),
    CHECK (driver_seat_heating BETWEEN {MIN_SEAT_HEATING} AND {MAX_SEAT_HEATING}),
    CHECK (passenger_seat_heating BETWEEN {MIN_SEAT_HEATING} AND {MAX_SEAT_HEATING}),
    CHECK (fan_speed BETWEEN {MIN_FAN_SPEED} AND {MAX_FAN_SPEED}),
    CHECK (volume BETWEEN {MIN_VOLUME} AND {MAX_VOLUME}),
    CHECK (ambient_light IN ({AMBIENT_LIGHT_SQL_VALUES}))
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_by_user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(user_id),
    CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE IF NOT EXISTS session_participants (
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    profile_id TEXT NULL,
    joined_at TEXT NOT NULL,
    PRIMARY KEY (session_id, user_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE SET NULL,
    CHECK (role IN ('driver', 'passenger'))
);
"""


def init_db() -> None:
    """Create the application tables if they do not already exist."""
    connection = get_connection()
    try:
        connection.executescript(SCHEMA)
        _migrate_profiles(connection)
        connection.commit()
    finally:
        connection.close()


def _migrate_profiles(connection) -> None:
    """Normalize profiles created with older temperature and zone rules."""
    connection.execute(
        """
        UPDATE profiles
        SET driver_temperature = MIN(MAX(driver_temperature, ?), ?),
            passenger_temperature = MIN(MAX(driver_temperature, ?), ?),
            passenger_seat_heating = driver_seat_heating
        """,
        (
            MIN_TEMPERATURE,
            MAX_TEMPERATURE,
            MIN_TEMPERATURE,
            MAX_TEMPERATURE,
        ),
    )
