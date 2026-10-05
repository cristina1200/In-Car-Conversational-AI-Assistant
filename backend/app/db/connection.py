from pathlib import Path
import sqlite3


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
DATABASE_PATH = DATA_DIR / "app.sqlite3"


def get_connection() -> sqlite3.Connection:
    """Return a configured connection to the local SQLite database."""
    database_path = Path(DATABASE_PATH).resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
