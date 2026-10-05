import json
import sqlite3
from typing import Any

from app.db.connection import get_connection


class UserRepository:
    def create(
        self,
        *,
        user_id: str,
        name: str,
        email: str,
        password_hash: str,
        created_at: str,
    ) -> sqlite3.Row:
        connection = get_connection()

        try:
            connection.execute(
                "INSERT INTO users "
                "(user_id, name, email, password_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, name, email, password_hash, created_at),
            )
            connection.commit()
            row = connection.execute(
                "SELECT user_id, name, email, voice_enrolled, "
                "created_at FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            raise RuntimeError("Created user could not be loaded")

        return row

    def get_by_id(self, user_id: str) -> sqlite3.Row | None:
        return self._get_one(
            "SELECT user_id, name, email, voice_enrolled, voice_embedding, "
            "created_at FROM users WHERE user_id = ?",
            (user_id,),
        )

    def get_by_email(self, email: str) -> sqlite3.Row | None:
        return self._get_one(
            "SELECT user_id, name, email, password_hash, voice_enrolled, "
            "voice_embedding, created_at FROM users WHERE email = ?",
            (email,),
        )

    def save_voice_embedding(
        self,
        user_id: str,
        embedding: list[float],
    ) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            payload = json.dumps(embedding).encode("utf-8")
            cursor = connection.execute(
                "UPDATE users SET voice_embedding = ?, voice_enrolled = 1 "
                "WHERE user_id = ?",
                (payload, user_id),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return None
            row = connection.execute(
                "SELECT user_id, name, email, voice_enrolled, voice_embedding, "
                "created_at FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            connection.commit()
            return row
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_voice_enrolled_users(self) -> list[sqlite3.Row]:
        connection = get_connection()

        try:
            return connection.execute(
                "SELECT user_id, name, email, voice_enrolled, voice_embedding FROM users "
                "WHERE voice_enrolled = 1 AND voice_embedding IS NOT NULL",
            ).fetchall()
        finally:
            connection.close()

    def list_voice_enrolled_users_for_session(
        self,
        session_id: str,
    ) -> list[sqlite3.Row]:
        connection = get_connection()

        try:
            return connection.execute(
                "SELECT u.user_id, u.name, u.voice_enrolled, u.voice_embedding "
                "FROM session_participants AS sp "
                "INNER JOIN users AS u ON u.user_id = sp.user_id "
                "WHERE sp.session_id = ? "
                "AND u.voice_enrolled = 1 "
                "AND u.voice_embedding IS NOT NULL "
                "ORDER BY sp.joined_at, u.user_id",
                (session_id,),
            ).fetchall()
        finally:
            connection.close()

    def email_exists(self, email: str) -> bool:
        connection = get_connection()

        try:
            row = connection.execute(
                "SELECT 1 FROM users WHERE email = ? LIMIT 1",
                (email,),
            ).fetchone()
        finally:
            connection.close()

        return row is not None

    def delete(self, user_id: str) -> bool:
        connection = get_connection()

        try:
            user_exists = connection.execute(
                "SELECT 1 FROM users WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()

            if user_exists is None:
                return False

            connection.execute(
                "DELETE FROM session_participants "
                "WHERE user_id = ? OR session_id IN ("
                "SELECT session_id FROM sessions "
                "WHERE created_by_user_id = ?"
                ")",
                (user_id, user_id),
            )
            connection.execute(
                "DELETE FROM sessions WHERE created_by_user_id = ?",
                (user_id,),
            )
            connection.execute(
                "DELETE FROM users WHERE user_id = ?",
                (user_id,),
            )
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _get_one(
        query: str,
        parameters: tuple[Any, ...],
    ) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            return connection.execute(query, parameters).fetchone()
        finally:
            connection.close()
