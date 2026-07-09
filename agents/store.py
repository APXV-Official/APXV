"""
APXV — Local SQLite Artifact Store (Phase 2)

Air-gapped, self-hosted, zero external dependencies.
Uses stdlib sqlite3 + content-addressable blob files on local disk.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import json
import sqlite3


SCHEMA_VERSION = 2


class SqliteArtifactStore:
    """Immutable artifact index with content-addressable blob storage."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.store_path = self.base_path / "managed" / "store"
        self.db_path = self._resolve_db_path()
        self.blobs_path = self.store_path / "blobs"
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.blobs_path.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _resolve_db_path(self) -> Path:
        """Prefer apxv.db; migrate legacy apx.db on first open."""
        apxv_path = self.store_path / "apxv.db"
        apx_path = self.store_path / "apx.db"
        if not apxv_path.exists() and apx_path.exists():
            apx_path.rename(apxv_path)
        return apxv_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    artifact_hash TEXT NOT NULL UNIQUE,
                    blob_relpath TEXT NOT NULL UNIQUE,
                    previous_hash TEXT,
                    written_at TEXT NOT NULL,
                    written_by TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_artifacts_name
                ON artifacts(name)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_specs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_type TEXT NOT NULL,
                    spec_id TEXT NOT NULL,
                    version TEXT,
                    content_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    previous_hash TEXT,
                    UNIQUE(spec_type, content_hash)
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO schema_meta (key, value)
                VALUES ('schema_version', ?)
                """,
                (str(SCHEMA_VERSION),),
            )
            self.ensure_governance_approval_schema(conn)
            conn.commit()

    def ensure_governance_approval_schema(self, conn: Optional[sqlite3.Connection] = None) -> None:
        owns_conn = conn is None
        conn = conn or self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_proposals (
                    id TEXT PRIMARY KEY,
                    spec_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    proposed_content_relpath TEXT NOT NULL,
                    proposed_by TEXT NOT NULL,
                    proposed_at TEXT NOT NULL,
                    summary TEXT,
                    current_content_hash TEXT,
                    approved_by TEXT,
                    approved_at TEXT,
                    approval_signature TEXT,
                    rejected_by TEXT,
                    rejected_at TEXT,
                    rejection_reason TEXT,
                    applied_at TEXT,
                    applied_content_hash TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_governance_proposals_status
                ON governance_proposals(status)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_active_approval (
                    spec_type TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    approved_at TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                UPDATE schema_meta SET value = ?
                WHERE key = 'schema_version' AND CAST(value AS INTEGER) < ?
                """,
                (str(SCHEMA_VERSION), SCHEMA_VERSION),
            )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn:
                conn.close()

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _utcnow(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def write_artifact(
        self,
        artifact: Dict[str, Any],
        name: str,
        written_by: str = "SqliteArtifactStore",
    ) -> Dict[str, Any]:
        artifact_json = json.dumps(artifact, sort_keys=True)
        artifact_hash = self.compute_hash(artifact_json)

        previous_hash = self.get_latest_artifact_hash()
        timestamp = self._utcnow().replace(":", "-").replace(".", "-")
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).lower()
        blob_name = f"{safe_name}_{artifact_hash[:16]}_{timestamp}.json"
        blob_relpath = f"blobs/{blob_name}"
        blob_path = self.store_path / "blobs" / blob_name

        if blob_path.exists():
            raise FileExistsError(f"Blob already exists for hash {artifact_hash}")

        wrapped = {
            "artifact": artifact,
            "written_by": written_by,
            "written_at": self._utcnow(),
            "artifact_hash": artifact_hash,
            "previous_artifact": previous_hash,
            "storage": "sqlite+cas",
        }
        blob_path.write_text(json.dumps(wrapped, indent=2, sort_keys=True), encoding="utf-8")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts
                (name, artifact_hash, blob_relpath, previous_hash, written_at, written_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_name,
                    artifact_hash,
                    blob_relpath,
                    previous_hash,
                    wrapped["written_at"],
                    written_by,
                ),
            )
            conn.commit()

        return {
            "path": str((self.store_path / blob_relpath).relative_to(self.base_path)).replace("\\", "/"),
            "absolute_path": str(blob_path),
            "hash": artifact_hash,
            "written_at": wrapped["written_at"],
            "filename": blob_name,
            "previous_artifact": previous_hash,
            "storage": "sqlite+cas",
        }

    def get_latest_artifact_hash(self) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT artifact_hash FROM artifacts ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return row["artifact_hash"] if row else None

    def read_artifact(self, identifier: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM artifacts
                WHERE artifact_hash = ? OR blob_relpath LIKE ?
                ORDER BY id DESC LIMIT 1
                """,
                (identifier, f"%{identifier}%"),
            ).fetchone()
        if not row:
            raise FileNotFoundError(f"Artifact not found in store: {identifier}")

        blob_path = self.store_path / row["blob_relpath"]
        data = json.loads(blob_path.read_text(encoding="utf-8"))
        stored_hash = data.get("artifact_hash")
        computed_hash = self.compute_hash(json.dumps(data["artifact"], sort_keys=True))
        if stored_hash and stored_hash != computed_hash:
            raise ValueError(f"Integrity check failed for artifact {row['artifact_hash']}")
        data["read_at"] = self._utcnow()
        data["store_record"] = dict(row)
        return data

    def count_artifacts(self, name_prefix: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) AS c FROM artifacts"
        params: List[Any] = []
        if name_prefix:
            query += " WHERE name LIKE ?"
            params.append(f"{name_prefix}%")
        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        return int(row["c"]) if row else 0

    def list_artifacts(
        self,
        name_prefix: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM artifacts"
        params: List[Any] = []
        if name_prefix:
            query += " WHERE name LIKE ?"
            params.append(f"{name_prefix}%")
        query += " ORDER BY id DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
        if offset is not None:
            query += " OFFSET ?"
            params.append(int(offset))

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def verify_artifact_chain(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM artifacts ORDER BY id ASC").fetchall()

        expected_previous = None
        issues: List[str] = []
        for row in rows:
            if row["previous_hash"] != expected_previous:
                issues.append(
                    f"Chain break at id={row['id']} hash={row['artifact_hash'][:16]}..."
                )
            blob_path = self.store_path / row["blob_relpath"]
            if not blob_path.exists():
                issues.append(f"Missing blob for {row['artifact_hash']}")
                continue
            data = json.loads(blob_path.read_text(encoding="utf-8"))
            computed = self.compute_hash(json.dumps(data["artifact"], sort_keys=True))
            if computed != row["artifact_hash"]:
                issues.append(f"Hash mismatch for {row['artifact_hash']}")
            expected_previous = row["artifact_hash"]

        return {
            "valid": len(issues) == 0,
            "artifact_count": len(rows),
            "issues": issues,
        }

    def register_governance_spec(
        self,
        spec_type: str,
        spec_id: str,
        version: str,
        content_hash: str,
        file_path: str,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            prev = conn.execute(
                """
                SELECT content_hash FROM governance_specs
                WHERE spec_type = ?
                ORDER BY id DESC LIMIT 1
                """,
                (spec_type,),
            ).fetchone()
            previous_hash = prev["content_hash"] if prev else None

            if previous_hash == content_hash:
                return {
                    "changed": False,
                    "spec_type": spec_type,
                    "content_hash": content_hash,
                }

            conn.execute(
                """
                INSERT OR IGNORE INTO governance_specs
                (spec_type, spec_id, version, content_hash, file_path, registered_at, previous_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spec_type,
                    spec_id,
                    version,
                    content_hash,
                    file_path,
                    self._utcnow(),
                    previous_hash,
                ),
            )
            conn.commit()

        return {
            "changed": True,
            "spec_type": spec_type,
            "spec_id": spec_id,
            "version": version,
            "content_hash": content_hash,
            "previous_hash": previous_hash,
            "registered_at": self._utcnow(),
        }

    def create_governance_proposal(
        self,
        proposal_id: str,
        spec_type: str,
        content_hash: str,
        proposed_content_relpath: str,
        proposed_by: str,
        summary: str = "",
        current_content_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        proposed_at = self._utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO governance_proposals (
                    id, spec_type, status, content_hash, proposed_content_relpath,
                    proposed_by, proposed_at, summary, current_content_hash
                ) VALUES (?, ?, 'proposed', ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    spec_type,
                    content_hash,
                    proposed_content_relpath,
                    proposed_by,
                    proposed_at,
                    summary,
                    current_content_hash,
                ),
            )
            conn.commit()
        return self.get_governance_proposal(proposal_id) or {}

    def get_governance_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM governance_proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_governance_proposal(self, proposal_id: str, **fields: Any) -> Dict[str, Any]:
        allowed = {
            "status",
            "approved_by",
            "approved_at",
            "approval_signature",
            "rejected_by",
            "rejected_at",
            "rejection_reason",
            "applied_at",
            "applied_content_hash",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            proposal = self.get_governance_proposal(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")
            return proposal

        assignments = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [proposal_id]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE governance_proposals SET {assignments} WHERE id = ?",
                values,
            )
            conn.commit()
        proposal = self.get_governance_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")
        return proposal

    def list_governance_proposals(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM governance_proposals
                ORDER BY proposed_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_active_approval(self, spec_type: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM governance_active_approval WHERE spec_type = ?",
                (spec_type,),
            ).fetchone()
        return dict(row) if row else None

    def set_active_approval(
        self,
        spec_type: str,
        content_hash: str,
        proposal_id: str,
        approved_at: str,
        applied_at: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO governance_active_approval
                (spec_type, content_hash, proposal_id, approved_at, applied_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(spec_type) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    proposal_id = excluded.proposal_id,
                    approved_at = excluded.approved_at,
                    applied_at = excluded.applied_at
                """,
                (spec_type, content_hash, proposal_id, approved_at, applied_at),
            )
            conn.commit()

    def list_governance_specs(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT g1.*
                FROM governance_specs g1
                INNER JOIN (
                    SELECT spec_type, MAX(id) AS max_id
                    FROM governance_specs
                    GROUP BY spec_type
                ) g2 ON g1.id = g2.max_id
                ORDER BY g1.spec_type
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def migrate_legacy_artifacts(self) -> int:
        """Index existing managed/artifacts/*.json into the store (idempotent)."""
        legacy_dir = self.base_path / "managed" / "artifacts"
        if not legacy_dir.exists():
            return 0

        imported = 0
        files = sorted(legacy_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                artifact = data.get("artifact", data)
                artifact_hash = data.get("artifact_hash") or self.compute_hash(
                    json.dumps(artifact, sort_keys=True)
                )
                with self._connect() as conn:
                    exists = conn.execute(
                        "SELECT 1 FROM artifacts WHERE artifact_hash = ?",
                        (artifact_hash,),
                    ).fetchone()
                if exists:
                    continue
                name = path.stem.split("_")[0] if "_" in path.stem else path.stem
                self.write_artifact(artifact, name=name, written_by="legacy_migration")
                imported += 1
            except Exception:
                continue
        return imported

    def get_status(self) -> Dict[str, Any]:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM artifacts").fetchone()["c"]
            gov_count = conn.execute("SELECT COUNT(*) AS c FROM governance_specs").fetchone()["c"]
        chain = self.verify_artifact_chain()
        return {
            "provider": "SqliteArtifactStore",
            "version": "2.0.0",
            "db_path": str(self.db_path.relative_to(self.base_path)).replace("\\", "/"),
            "artifacts_count": count,
            "governance_records": gov_count,
            "chain_valid": chain["valid"],
            "air_gapped": True,
        }