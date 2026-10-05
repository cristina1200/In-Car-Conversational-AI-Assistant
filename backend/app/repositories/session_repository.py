import sqlite3

from app.db.connection import get_connection


SESSION_COLUMNS = (
    "session_id, created_by_user_id, status, created_at"
)
PARTICIPANT_COLUMNS = (
    "session_id, user_id, role, profile_id, joined_at"
)


class SessionRepository:
    def create_session(
        self,
        *,
        session_id: str,
        created_by_user_id: str,
        created_at: str,
    ) -> sqlite3.Row:
        connection = get_connection()

        try:
            connection.execute(
                "INSERT INTO sessions "
                "(session_id, created_by_user_id, status, created_at) "
                "VALUES (?, ?, 'active', ?)",
                (session_id, created_by_user_id, created_at),
            )
            row = connection.execute(
                f"SELECT {SESSION_COLUMNS} FROM sessions "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        if row is None:
            raise RuntimeError("Created session could not be loaded")

        return row

    def get_by_id(self, session_id: str) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            return connection.execute(
                f"SELECT {SESSION_COLUMNS} FROM sessions "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        finally:
            connection.close()

    def add_participant(
        self,
        *,
        session_id: str,
        user_id: str,
        role: str,
        profile_id: str | None,
        joined_at: str,
    ) -> sqlite3.Row:
        connection = get_connection()

        try:
            connection.execute(
                "INSERT INTO session_participants "
                "(session_id, user_id, role, profile_id, joined_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, role, profile_id, joined_at),
            )
            row = connection.execute(
                f"SELECT {PARTICIPANT_COLUMNS} "
                "FROM session_participants "
                "WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        if row is None:
            raise RuntimeError("Created participant could not be loaded")

        return row

    def get_participant(
        self,
        *,
        session_id: str,
        user_id: str,
    ) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            return connection.execute(
                f"SELECT {PARTICIPANT_COLUMNS} "
                "FROM session_participants "
                "WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
        finally:
            connection.close()

    def list_participants(self, session_id: str) -> list[sqlite3.Row]:
        connection = get_connection()

        try:
            return connection.execute(
                f"SELECT {PARTICIPANT_COLUMNS} "
                "FROM session_participants "
                "WHERE session_id = ? ORDER BY joined_at, user_id",
                (session_id,),
            ).fetchall()
        finally:
            connection.close()

    def participant_exists(self, session_id: str, user_id: str) -> bool:
        return self.get_participant(
            session_id=session_id,
            user_id=user_id,
        ) is not None

    def has_driver(self, session_id: str) -> bool:
        connection = get_connection()

        try:
            row = connection.execute(
                "SELECT 1 FROM session_participants "
                "WHERE session_id = ? AND role = 'driver' LIMIT 1",
                (session_id,),
            ).fetchone()
        finally:
            connection.close()

        return row is not None

    def update_participant_role(
        self,
        *,
        session_id: str,
        user_id: str,
        role: str,
    ) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            cursor = connection.execute(
                "UPDATE session_participants SET role = ? "
                "WHERE session_id = ? AND user_id = ?",
                (role, session_id, user_id),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return None

            row = connection.execute(
                f"SELECT {PARTICIPANT_COLUMNS} "
                "FROM session_participants "
                "WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            connection.commit()
            return row
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def remove_participant(
        self,
        *,
        session_id: str,
        user_id: str,
    ) -> bool:
        connection = get_connection()

        try:
            cursor = connection.execute(
                "DELETE FROM session_participants "
                "WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return False
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def associate_profile(
        self,
        *,
        session_id: str,
        user_id: str,
        profile_id: str,
    ) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            cursor = connection.execute(
                "UPDATE session_participants SET profile_id = ? "
                "WHERE session_id = ? AND user_id = ?",
                (profile_id, session_id, user_id),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return None

            row = connection.execute(
                f"SELECT {PARTICIPANT_COLUMNS} "
                "FROM session_participants "
                "WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            connection.commit()
            return row
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def close_session(self, session_id: str) -> sqlite3.Row | None:
        connection = get_connection()

        try:
            cursor = connection.execute(
                "UPDATE sessions SET status = 'inactive' "
                "WHERE session_id = ? AND status = 'active'",
                (session_id,),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return None

            row = connection.execute(
                f"SELECT {SESSION_COLUMNS} FROM sessions "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            connection.commit()
            return row
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
