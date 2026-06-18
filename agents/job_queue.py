"""
APX v1 — Local SQLite Job Queue (Phase 4 / Step 1)

Durable job tracking for pipeline runs. Stdlib sqlite3 only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sqlite3
import uuid


class JobQueue:
    """SQLite-backed job queue for local APX pipeline execution."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
            )
            conn.commit()

    def _utcnow(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def enqueue(self, job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        job_id = f"job-{uuid.uuid4().hex[:16]}"
        created_at = self._utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, job_type, status, payload, created_at)
                VALUES (?, ?, 'queued', ?, ?)
                """,
                (job_id, job_type, json.dumps(payload), created_at),
            )
            conn.commit()
        return {"job_id": job_id, "status": "queued", "created_at": created_at}

    def claim_next(self, job_type: str = "pipeline") -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'queued' AND job_type = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (job_type,),
            ).fetchone()
            if not row:
                return None
            started_at = self._utcnow()
            conn.execute(
                """
                UPDATE jobs
                SET status = 'running', started_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (started_at, row["id"]),
            )
            conn.commit()
            if conn.total_changes == 0:
                return None
        job = dict(row)
        job["status"] = "running"
        job["started_at"] = started_at
        job["payload"] = json.loads(job["payload"] or "{}")
        return job

    def complete(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'completed', result = ?, completed_at = ?, error = NULL
                WHERE id = ?
                """,
                (json.dumps(result), self._utcnow(), job_id),
            )
            conn.commit()

    def fail(self, job_id: str, error: str, retry: bool = False) -> None:
        with self._connect() as conn:
            if retry:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'queued', error = ?, retry_count = retry_count + 1,
                        started_at = NULL, completed_at = NULL
                    WHERE id = ?
                    """,
                    (error, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'failed', error = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (error, self._utcnow(), job_id),
                )
            conn.commit()

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        if data.get("payload"):
            data["payload"] = json.loads(data["payload"])
        if data.get("result"):
            data["result"] = json.loads(data["result"])
        return data