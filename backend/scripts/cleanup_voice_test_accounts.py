from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.sqlite3"
BACKUP_DIR = DB_PATH.parent


def list_target_users(connection: sqlite3.Connection):
    rows = connection.execute(
        """
        SELECT user_id, name, email, voice_enrolled, voice_embedding IS NOT NULL AS has_embedding, created_at
        FROM users
        WHERE name IN ('Alice', 'Bob') AND voice_enrolled = 1
        ORDER BY created_at ASC, user_id ASC
        LIMIT 2
        """
    ).fetchall()
    return rows


def backup_database(src: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = src.with_name(f"{src.stem}.backup-{timestamp}{src.suffix}")
    shutil.copy2(src, backup_path)
    return backup_path


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        targets = list_target_users(connection)
        if not targets:
            print("No stale Alice/Bob voice-test accounts found.")
            return

        print("Accounts selected for cleanup:")
        for row in targets:
            print(f"- user_id={row['user_id']} | name={row['name']} | email={row['email']} | created_at={row['created_at']}")

        backup_path = backup_database(DB_PATH)
        print(f"Backup created: {backup_path}")

        user_ids = [row["user_id"] for row in targets]
        placeholders = ", ".join("?" for _ in user_ids)

        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            f"DELETE FROM session_participants WHERE user_id IN ({placeholders})",
            user_ids,
        )
        connection.execute(
            f"DELETE FROM sessions WHERE created_by_user_id IN ({placeholders})",
            user_ids,
        )
        connection.execute(
            f"DELETE FROM profiles WHERE user_id IN ({placeholders})",
            user_ids,
        )
        connection.execute(
            f"DELETE FROM users WHERE user_id IN ({placeholders})",
            user_ids,
        )
        connection.commit()

        remaining = connection.execute(
            f"SELECT user_id, name, email, voice_enrolled, voice_embedding FROM users WHERE user_id IN ({placeholders})",
            user_ids,
        ).fetchall()

        print("Post-cleanup verification:")
        if remaining:
            print("Still present:")
            for row in remaining:
                print(row)
        else:
            print("No target accounts remain in users.")

        session_rows = connection.execute(
            f"SELECT session_id, created_by_user_id FROM sessions WHERE created_by_user_id IN ({placeholders})",
            user_ids,
        ).fetchall()
        if session_rows:
            print("Unexpected remaining sessions:")
            for row in session_rows:
                print(row)
        else:
            print("No sessions remain for target users.")

        profile_rows = connection.execute(
            f"SELECT profile_id, user_id FROM profiles WHERE user_id IN ({placeholders})",
            user_ids,
        ).fetchall()
        if profile_rows:
            print("Unexpected remaining profiles:")
            for row in profile_rows:
                print(row)
        else:
            print("No profiles remain for target users.")

        voice_rows = connection.execute(
            f"SELECT user_id, name, voice_enrolled, voice_embedding IS NOT NULL AS has_embedding FROM users WHERE user_id IN ({placeholders})",
            user_ids,
        ).fetchall()
        if voice_rows:
            print("Unexpected remaining voice data:")
            for row in voice_rows:
                print(row)
        else:
            print("No target voice embeddings remain.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
