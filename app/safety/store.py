import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SafetyStore:
    """SQLite-backed audit log + human-in-the-loop approval queue.

    Pass db_path=":memory:" for tests; a real file path persists across
    process restarts (the default, settings.safety_db_path).
    """

    def __init__(self, db_path: str = ":memory:"):
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                message TEXT NOT NULL,
                category TEXT,
                sentiment TEXT,
                action TEXT NOT NULL,
                input_flagged INTEGER NOT NULL,
                output_flagged INTEGER NOT NULL,
                flag_reasons TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                message TEXT NOT NULL,
                draft_response TEXT NOT NULL,
                category TEXT,
                action TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reviewer_note TEXT,
                decided_at TEXT
            )
            """
        )
        self._conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_audit(
        self,
        *,
        message: str,
        category: str | None,
        sentiment: str | None,
        action: str,
        input_flagged: bool,
        output_flagged: bool,
        flag_reasons: list[str],
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO audit_log
                (created_at, message, category, sentiment, action,
                 input_flagged, output_flagged, flag_reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._now(),
                message,
                category,
                sentiment,
                action,
                int(input_flagged),
                int(output_flagged),
                json.dumps(flag_reasons),
            ),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_audit(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def enqueue_approval(
        self, *, message: str, draft_response: str, category: str | None, action: str
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO approval_queue
                (created_at, message, draft_response, category, action, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (self._now(), message, draft_response, category, action),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_pending_approvals(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM approval_queue WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    def decide_approval(
        self, approval_id: int, approved: bool, note: str | None = None
    ) -> dict | None:
        status = "approved" if approved else "rejected"
        self._conn.execute(
            """
            UPDATE approval_queue
            SET status = ?, reviewer_note = ?, decided_at = ?
            WHERE id = ?
            """,
            (status, note, self._now(), approval_id),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM approval_queue WHERE id = ?", (approval_id,)
        ).fetchone()
        return dict(row) if row else None
