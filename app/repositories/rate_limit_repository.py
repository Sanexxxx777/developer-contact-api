import sqlite3
import time
from pathlib import Path
from threading import Lock


class RateLimitRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._lock = Lock()

    def consume(self, identity_hash: str, limit: int, window_seconds: int) -> int | None:
        now = int(time.time())
        boundary = now - window_seconds
        with self._lock, sqlite3.connect(self.database_path, timeout=5) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM rate_limit_events WHERE created_at < ?", (boundary,))
            row = connection.execute(
                """
                SELECT COUNT(*), MIN(created_at)
                FROM rate_limit_events
                WHERE identity_hash = ? AND created_at >= ?
                """,
                (identity_hash, boundary),
            ).fetchone()
            if row[0] >= limit:
                return max(1, window_seconds - (now - row[1]))
            connection.execute(
                "INSERT INTO rate_limit_events (identity_hash, created_at) VALUES (?, ?)",
                (identity_hash, now),
            )
        return None
