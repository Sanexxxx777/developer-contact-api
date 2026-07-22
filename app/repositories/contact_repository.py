import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.models.contact import AIAnalysis, ContactCreate


class ContactRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._lock = Lock()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS contacts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    ai_analysis TEXT NOT NULL,
                    ai_fallback_used INTEGER NOT NULL,
                    delivery_status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rate_limit_events (
                    identity_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_rate_limit_identity_time
                ON rate_limit_events(identity_hash, created_at);
                """
            )

    def create(
        self, contact: ContactCreate, analysis: AIAnalysis, fallback_used: bool
    ) -> tuple[str, datetime]:
        contact_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO contacts
                (id, name, phone, email, comment, ai_analysis,
                 ai_fallback_used, delivery_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    contact_id,
                    contact.name,
                    contact.phone,
                    str(contact.email),
                    contact.comment,
                    analysis.model_dump_json(),
                    int(fallback_used),
                    created_at.isoformat(),
                ),
            )
        return contact_id, created_at

    def set_delivery_status(self, contact_id: str, status: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE contacts SET delivery_status = ? WHERE id = ?", (status, contact_id)
            )

    def metrics(self) -> dict[str, object]:
        with self._connect() as connection:
            totals = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(delivery_status = 'delivered') AS delivered,
                       SUM(delivery_status = 'failed') AS failed,
                       SUM(ai_fallback_used) AS fallbacks
                FROM contacts
                """
            ).fetchone()
            analyses = connection.execute("SELECT ai_analysis FROM contacts").fetchall()
        by_category: dict[str, int] = {}
        for row in analyses:
            category = json.loads(row[0])["category"]
            by_category[category] = by_category.get(category, 0) + 1
        return {
            "total_contacts": totals[0] or 0,
            "delivered_contacts": totals[1] or 0,
            "failed_contacts": totals[2] or 0,
            "ai_fallbacks": totals[3] or 0,
            "by_category": by_category,
        }

    def ping(self) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection
