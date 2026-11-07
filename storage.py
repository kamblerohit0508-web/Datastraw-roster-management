"""SQLite persistence for the RosterFlow workspace."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "rosterflow.db"


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workspace (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payload TEXT NOT NULL
            )
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def load_workspace():
    """Return the saved workspace, or None if this is a new installation."""
    with _connect() as connection:
        row = connection.execute(
            "SELECT payload FROM workspace WHERE id = 1"
        ).fetchone()

    return json.loads(row[0]) if row else None


def save_workspace(workspace):
    """Save the workspace as one consistent JSON snapshot."""
    payload = json.dumps(workspace, ensure_ascii=False)

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO workspace (id, payload)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET payload = excluded.payload
            """,
            (payload,),
        )
