from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.sqlite3"


def backup_database(path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_name(f"{path.stem}.backup-{timestamp}{path.suffix}")
    shutil.copy2(path, backup_path)
    return backup_path


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        users = connection.execute(
            "SELECT user_id, name, email, voice_enrolled, created_at FROM users ORDER BY created_at, user_id"
        ).fetchall()

        print(f"Users to delete: {len(users)}")
        for row in users:
            print(
                f"- user_id={row['user_id']} | name={row['name']} | email={row['email']} | "
                f"voice_enrolled={row['voice_enrolled']} | created_at={row['created_at']}"
            )

        backup_path = backup_database(DB_PATH)
        print(f"Backup created: {backup_path}")

        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM session_participants")
            connection.execute("DELETE FROM sessions")
            connection.execute("DELETE FROM profiles")
            connection.execute("DELETE FROM users")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        counts = {
            "users": connection.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "profiles": connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0],
            "sessions": connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
            "session_participants": connection.execute("SELECT COUNT(*) FROM session_participants").fetchone()[0],
            "users_with_voice_embedding": connection.execute(
                "SELECT COUNT(*) FROM users WHERE voice_embedding IS NOT NULL"
            ).fetchone()[0],
        }

        print("Post-cleanup verification:")
        for name, value in counts.items():
            print(f"- {name}: {value}")

        if any(value != 0 for value in counts.values()):
            raise RuntimeError(f"Cleanup incomplete. Counts: {counts}")

        print("Verification passed: all user/session/profile data has been removed from the database.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
