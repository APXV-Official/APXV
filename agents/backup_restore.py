"""
APXV — Backup & Restore (Phase 4 / Step 4)

Air-gapped backup of managed/ state and ZK key material (governance + entity).
Stdlib only: tarfile + SHA-256 manifest for verify-before-restore.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import tarfile
import uuid

BACKUP_SCHEMA_VERSION = "1.0.0"
MANIFEST_NAME = "apx-backup-manifest.json"
DEFAULT_COMPONENTS = (
    "managed",
    "rust/apxv-circuits/keys",
    "rust/apxv-zk/keys",
)

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    "backups",
}


class BackupRestoreError(Exception):
    """Raised when backup or restore operations fail."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def default_backup_dir(base_path: Path) -> Path:
    return base_path / "managed" / "backups"


class BackupManager:
    """Create, verify, list, and restore local APX backups."""

    def __init__(self, base_path: Optional[Path] = None, audit_logger: Any = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.backup_dir = default_backup_dir(self.base_path)
        self.audit_logger = audit_logger

    def _log(self, event_type: str, data: Dict[str, Any]) -> None:
        if self.audit_logger is not None:
            self.audit_logger.log_event(event_type=event_type, data=data)

    def _component_roots(self) -> List[Tuple[str, Path]]:
        roots = []
        for component in DEFAULT_COMPONENTS:
            path = self.base_path / component
            if path.exists():
                roots.append((component, path))
        return roots

    def _iter_backup_files(self) -> List[Tuple[str, Path]]:
        files: List[Tuple[str, Path]] = []
        for component, root in self._component_roots():
            if not root.is_dir():
                if root.is_file():
                    files.append((component.replace("\\", "/"), root))
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
                    continue
                rel = path.relative_to(self.base_path).as_posix()
                files.append((rel, path))
        return files

    def build_manifest(self) -> Dict[str, Any]:
        entries = []
        for rel, path in self._iter_backup_files():
            entries.append(
                {
                    "path": rel,
                    "sha256": _sha256_file(path),
                    "size": path.stat().st_size,
                }
            )
        entries.sort(key=lambda item: item["path"])
        manifest = {
            "schema_version": BACKUP_SCHEMA_VERSION,
            "backup_id": f"backup-{uuid.uuid4().hex[:12]}",
            "created_at": _utcnow(),
            "components": list(DEFAULT_COMPONENTS),
            "file_count": len(entries),
            "files": entries,
        }
        manifest["aggregate_hash"] = hashlib.sha256(
            _canonical_json({"files": entries}).encode("utf-8")
        ).hexdigest()
        return manifest

    def create_backup(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        manifest = self.build_manifest()
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            output_path = self.backup_dir / f"apx-backup-{stamp}.tar.gz"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        with tarfile.open(output_path, "w:gz") as archive:
            manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
            manifest_info = tarfile.TarInfo(name=MANIFEST_NAME)
            manifest_info.size = len(manifest_bytes)
            archive.addfile(manifest_info, fileobj=_BytesIO(manifest_bytes))

            for rel, path in self._iter_backup_files():
                archive.add(path, arcname=rel)

        result = {
            "backup_id": manifest["backup_id"],
            "path": str(output_path),
            "relative_path": str(output_path.relative_to(self.base_path)).replace("\\", "/")
            if output_path.is_relative_to(self.base_path)
            else str(output_path),
            "created_at": manifest["created_at"],
            "file_count": manifest["file_count"],
            "aggregate_hash": manifest["aggregate_hash"],
            "size_bytes": output_path.stat().st_size,
        }
        self._log("backup_created", result)
        return result

    def read_manifest(self, archive_path: Path) -> Dict[str, Any]:
        archive_path = Path(archive_path)
        if not archive_path.exists():
            raise BackupRestoreError(f"Backup archive not found: {archive_path}")

        try:
            archive_handle = tarfile.open(archive_path, "r:gz")
        except (tarfile.ReadError, OSError) as exc:
            raise BackupRestoreError(f"Invalid backup archive: {exc}") from exc

        with archive_handle as archive:
            try:
                manifest_member = archive.getmember(MANIFEST_NAME)
            except KeyError as exc:
                raise BackupRestoreError("Backup manifest missing from archive") from exc
            extracted = archive.extractfile(manifest_member)
            if extracted is None:
                raise BackupRestoreError("Unable to read backup manifest")
            return json.loads(extracted.read().decode("utf-8"))

    def verify_backup(self, archive_path: Path) -> Dict[str, Any]:
        manifest = self.read_manifest(archive_path)
        issues = []

        if manifest.get("schema_version") != BACKUP_SCHEMA_VERSION:
            issues.append(f"Unsupported schema: {manifest.get('schema_version')}")

        files = manifest.get("files", [])
        expected_aggregate = hashlib.sha256(
            _canonical_json({"files": files}).encode("utf-8")
        ).hexdigest()
        if manifest.get("aggregate_hash") != expected_aggregate:
            issues.append("Manifest aggregate hash mismatch")

        try:
            archive_handle = tarfile.open(archive_path, "r:gz")
        except (tarfile.ReadError, OSError) as exc:
            raise BackupRestoreError(f"Invalid backup archive: {exc}") from exc

        with archive_handle as archive:
            members = {m.name for m in archive.getmembers() if m.isfile()}
            if MANIFEST_NAME not in members:
                issues.append("Manifest member missing")

            for entry in files:
                rel = entry["path"]
                if rel not in members:
                    issues.append(f"Missing file in archive: {rel}")
                    continue
                extracted = archive.extractfile(rel)
                if extracted is None:
                    issues.append(f"Unreadable archive member: {rel}")
                    continue
                digest = hashlib.sha256(extracted.read()).hexdigest()
                if digest != entry.get("sha256"):
                    issues.append(f"Hash mismatch: {rel}")

        return {
            "valid": len(issues) == 0,
            "backup_id": manifest.get("backup_id"),
            "created_at": manifest.get("created_at"),
            "file_count": manifest.get("file_count"),
            "issues": issues,
        }

    def list_backups(self) -> List[Dict[str, Any]]:
        if not self.backup_dir.exists():
            return []
        backups = []
        for path in sorted(self.backup_dir.glob("apx-backup-*.tar.gz"), reverse=True):
            try:
                manifest = self.read_manifest(path)
                verification = self.verify_backup(path)
                backups.append(
                    {
                        "filename": path.name,
                        "path": str(path),
                        "backup_id": manifest.get("backup_id"),
                        "created_at": manifest.get("created_at"),
                        "file_count": manifest.get("file_count"),
                        "size_bytes": path.stat().st_size,
                        "valid": verification["valid"],
                    }
                )
            except BackupRestoreError as exc:
                backups.append(
                    {
                        "filename": path.name,
                        "path": str(path),
                        "valid": False,
                        "error": str(exc),
                    }
                )
        return backups

    def restore_backup(
        self,
        archive_path: Path,
        *,
        dry_run: bool = False,
        create_safety_backup: bool = True,
    ) -> Dict[str, Any]:
        archive_path = Path(archive_path)
        verification = self.verify_backup(archive_path)
        if not verification["valid"]:
            raise BackupRestoreError(
                "Backup verification failed: " + "; ".join(verification["issues"])
            )

        manifest = self.read_manifest(archive_path)
        if dry_run:
            return {
                "dry_run": True,
                "backup_id": manifest.get("backup_id"),
                "file_count": manifest.get("file_count"),
                "verified": True,
            }

        safety_backup = None
        if create_safety_backup:
            safety_backup = self.create_backup(
                self.backup_dir / f"pre-restore-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.tar.gz"
            )

        restored_files = []
        with tarfile.open(archive_path, "r:gz") as archive:
            for entry in manifest.get("files", []):
                rel = entry["path"]
                member = archive.getmember(rel)
                target = self.base_path / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise BackupRestoreError(f"Failed to extract {rel}")
                target.write_bytes(extracted.read())
                restored_files.append(rel)

        result = {
            "backup_id": manifest.get("backup_id"),
            "restored_file_count": len(restored_files),
            "safety_backup": safety_backup,
            "archive": str(archive_path),
        }
        self._log("backup_restored", result)
        return result


class _BytesIO:
    """Minimal read-only bytes buffer for tarfile.addfile."""

    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk