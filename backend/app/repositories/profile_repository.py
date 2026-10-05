import sqlite3
from typing import Any

from app.db.connection import get_connection


PROFILE_COLUMNS = (
    "profile_id, user_id, profile_name, is_default, "
    "driver_temperature, passenger_temperature, "
    "driver_seat_heating, passenger_seat_heating, fan_speed, volume, "
    "ambient_light, created_at, updated_at"
)


class ProfileRepository:
    def user_exists(self, user_id: str) -> bool:
        connection = get_connection()

        try:
            row = connection.execute(
                "SELECT 1 FROM users WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
        finally:
            connection.close()

        return row is not None

    def create_profile(
        self,
        *,
        profile_id: str,
        user_id: str,
        profile_name: str,
        is_default: bool,
        driver_temperature: int,
        passenger_temperature: int,
        driver_seat_heating: int,
        passenger_seat_heating: int,
        fan_speed: int,
        volume: int,
        ambient_light: str,
        created_at: str,
        updated_at: str,
        replace_existing_defaults: bool = False,
    ) -> sqlite3.Row:
        connection = get_connection()

        try:
            if replace_existing_defaults:
                connection.execute(
                    "UPDATE profiles SET is_default = 0 "
                    "WHERE user_id = ?",
                    (user_id,),
                )

            connection.execute(
                "INSERT INTO profiles ("
                "profile_id, user_id, profile_name, is_default, "
                "driver_temperature, passenger_temperature, "
                "driver_seat_heating, passenger_seat_heating, fan_speed, "
                "volume, ambient_light, created_at, updated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    profile_id,
                    user_id,
                    profile_name,
                    int(is_default),
                    driver_temperature,
                    passenger_temperature,
                    driver_seat_heating,
                    passenger_seat_heating,
                    fan_speed,
                    volume,
                    ambient_light,
                    created_at,
                    updated_at,
                ),
            )
            row = connection.execute(
                f"SELECT {PROFILE_COLUMNS} FROM profiles "
                "WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        if row is None:
            raise RuntimeError("Created profile could not be loaded")

        return row

    def get_by_id(self, profile_id: str) -> sqlite3.Row | None:
        return self._get_one(
            f"SELECT {PROFILE_COLUMNS} FROM profiles "
            "WHERE profile_id = ?",
            (profile_id,),
        )

    def list_by_user_id(self, user_id: str) -> list[sqlite3.Row]:
        connection = get_connection()

        try:
            return connection.execute(
                f"SELECT {PROFILE_COLUMNS} FROM profiles "
                "WHERE user_id = ? ORDER BY is_default DESC, profile_name",
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

    def update_profile(
        self,
        *,
        profile_id: str,
        user_id: str,
        updates: dict[str, Any],
        updated_at: str,
    ) -> sqlite3.Row | None:
        if not updates:
            return self.get_by_id(profile_id)

        allowed_columns = {
            "profile_name",
            "is_default",
            "driver_temperature",
            "passenger_temperature",
            "driver_seat_heating",
            "passenger_seat_heating",
            "fan_speed",
            "volume",
            "ambient_light",
        }
        invalid_columns = set(updates) - allowed_columns
        if invalid_columns:
            raise ValueError("Unsupported profile fields")

        assignments = [f"{column} = ?" for column in updates]
        values = [
            int(value) if column == "is_default" else value
            for column, value in updates.items()
        ]
        assignments.append("updated_at = ?")
        values.extend([updated_at, profile_id, user_id])

        connection = get_connection()

        try:
            if updates.get("is_default") is True:
                connection.execute(
                    "UPDATE profiles SET is_default = 0 "
                    "WHERE user_id = ?",
                    (user_id,),
                )

            cursor = connection.execute(
                "UPDATE profiles SET "
                + ", ".join(assignments)
                + " WHERE profile_id = ? AND user_id = ?",
                values,
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return None

            row = connection.execute(
                f"SELECT {PROFILE_COLUMNS} FROM profiles "
                "WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            connection.commit()
            return row
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def set_default_profile(
        self,
        *,
        profile_id: str,
        user_id: str,
    ) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            connection.execute(
                "UPDATE profiles SET is_default = 0 "
                "WHERE user_id = ?",
                (user_id,),
            )
            cursor = connection.execute(
                "UPDATE profiles SET is_default = 1 "
                "WHERE profile_id = ? AND user_id = ?",
                (profile_id, user_id),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return None

            connection.commit()
            return connection.execute(
                f"SELECT {PROFILE_COLUMNS} FROM profiles "
                "WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
        finally:
            connection.close()

    def unset_default_profiles_for_user(
        self,
        user_id: str,
        *,
        exclude_profile_id: str | None = None,
    ) -> None:
        connection = get_connection()

        try:
            query = (
                "UPDATE profiles SET is_default = 0 "
                "WHERE user_id = ?"
            )
            parameters: tuple[str, ...] = (user_id,)
            if exclude_profile_id is not None:
                query += " AND profile_id != ?"
                parameters += (exclude_profile_id,)

            connection.execute(query, parameters)
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _get_one(
        query: str,
        parameters: tuple[str, ...],
    ) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            return connection.execute(query, parameters).fetchone()
        finally:
            connection.close()
