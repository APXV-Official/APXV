"""
APXV — Artifact Provider (Phase 2 Foundation)

This module defines the IArtifactProvider interface and a production-grade
FileArtifactProvider implementation.

Phase 2 Goals:
- Strong immutability guarantees (no overwrites, content integrity)
- Content-addressable storage foundation
- Clear separation between specification reading and artifact persistence
- Auditability-ready design (hash chaining, provenance metadata)

All code is original work written for APXV.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Protocol, TYPE_CHECKING
from datetime import datetime, timezone
import hashlib
import json

if TYPE_CHECKING:
    from .store import SqliteArtifactStore


def _utcnow_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _utcnow_filename() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat().replace(":", "-").replace(".", "-")


class IArtifactProvider(Protocol):
    """
    Interface for all artifact providers in APX.

    Implementations must guarantee:
    - Immutability: Once written, artifacts cannot be modified or deleted.
    - Integrity: Every read returns verified content or raises an error.
    - Auditability: Operations produce sufficient metadata for chaining.
    """

    def read_specification(self, spec_type: str) -> Dict[str, Any]:
        """Read a governed specification (rule, workflow, or knowledge)."""
        ...

    def write_artifact(self, artifact: Dict[str, Any], name: str) -> Dict[str, Any]:
        """Write a new governed artifact immutably."""
        ...

    def read_artifact(self, identifier: str) -> Dict[str, Any]:
        """Read a previously written artifact by identifier."""
        ...


class MinimalArtifactProvider:
    """
    Legacy minimal implementation retained for backward compatibility.
    New code should prefer FileArtifactProvider.
    """
    """
    The smallest viable artifact provider for APXV.

    Agents should use this instead of direct Path reads.
    """

    def __init__(self, base_path: Path = None):
        if base_path is None:
            # Default to APXV root (parent of agents/)
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)

        self.managed_path = self.base_path / "managed"
        self.artifacts_path = self.managed_path / "artifacts"

        # Ensure artifacts directory exists
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        # Mapping of logical spec names to their markdown files
        self._spec_map = {
            "rule": "rules/rule1.md",
            "workflow": "workflows/workflow1.md",
            "knowledge": "knowledge/knowledge1.md",
        }

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def read_specification(self, spec_type: str) -> Dict[str, Any]:
        """
        Read one of the core governed specifications.

        Args:
            spec_type: One of "rule", "workflow", or "knowledge"

        Returns:
            Dict containing: content, hash, id, version, file_path, read_at
        """
        if spec_type not in self._spec_map:
            raise ValueError(f"Unknown specification type: {spec_type}. "
                             f"Valid types: {list(self._spec_map.keys())}")

        relative_path = self._spec_map[spec_type]
        full_path = self.managed_path / relative_path

        if not full_path.exists():
            raise FileNotFoundError(f"Specification file not found: {full_path}")

        content = full_path.read_text(encoding="utf-8")
        file_hash = self._compute_hash(content)

        # Extract ID and version from the first few lines (simple convention)
        id_line = next((line for line in content.splitlines() if line.startswith("**ID:**")), "")
        version_line = next((line for line in content.splitlines() if "Version" in line), "")

        spec_id = id_line.split("**ID:**")[-1].strip() if id_line else f"APX-{spec_type.upper()}-001"
        version = version_line.split("Version")[-1].strip().strip("*") if version_line else "1.0.0"

        return {
            "spec_type": spec_type,
            "content": content,
            "hash": file_hash,
            "id": spec_id,
            "version": version,
            "file_path": str(relative_path),
            "read_at": _utcnow_z(),
        }

    def write_artifact(self, artifact: Dict[str, Any], name: str) -> Dict[str, Any]:
        """
        Write a new governed artifact (e.g. proposed_artifact or attested_result).

        The artifact is stored as JSON with embedded metadata for auditability.

        Args:
            artifact: The full artifact dictionary to persist
            name: Logical name for the artifact (will be used in filename)

        Returns:
            Dict with write metadata: path, hash, written_at
        """
        timestamp = _utcnow_filename()
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).lower()
        filename = f"{safe_name}_{timestamp}.json"
        full_path = self.artifacts_path / filename

        # Wrap with provenance metadata
        wrapped = {
            "artifact": artifact,
            "written_by": "MinimalArtifactProvider",
            "written_at": _utcnow_z(),
            "artifact_hash": self._compute_hash(json.dumps(artifact, sort_keys=True)),
        }

        full_path.write_text(json.dumps(wrapped, indent=2, sort_keys=True), encoding="utf-8")

        return {
            "path": str(full_path.relative_to(self.base_path)),
            "absolute_path": str(full_path),
            "hash": wrapped["artifact_hash"],
            "written_at": wrapped["written_at"],
            "filename": filename,
        }

    def read_artifact(self, filename: str) -> Dict[str, Any]:
        """Read a previously written artifact by filename."""
        full_path = self.artifacts_path / filename
        if not full_path.exists():
            raise FileNotFoundError(f"Artifact not found: {full_path}")

        content = full_path.read_text(encoding="utf-8")
        data = json.loads(content)
        data["read_at"] = _utcnow_z()
        return data

    def list_artifacts(self) -> list:
        """List all written artifacts (newest first)."""
        files = sorted(
            self.artifacts_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return [f.name for f in files]

    def get_status(self) -> Dict[str, Any]:
        """Return basic status of the provider."""
        return {
            "provider": "MinimalArtifactProvider",
            "version": "0.1.0",
            "artifacts_count": len(self.list_artifacts()),
        }


class FileArtifactProvider:
    """
    Phase 2 production-grade artifact provider.

    Guarantees:
    - Immutability: Artifacts are written once and never modified.
    - Content integrity: Every read verifies the stored hash.
    - Content-addressable foundation: Artifacts can be referenced by hash.
    - Audit-ready: Every write produces provenance metadata suitable for chaining.
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)

        self.managed_path = self.base_path / "managed"
        self.artifacts_path = self.managed_path / "artifacts"
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        # Specification mapping (same as Minimal for compatibility)
        self._spec_map = {
            "rule": "rules/rule1.md",
            "workflow": "workflows/workflow1.md",
            "knowledge": "knowledge/knowledge1.md",
        }

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def read_specification(self, spec_type: str) -> Dict[str, Any]:
        if spec_type not in self._spec_map:
            raise ValueError(f"Unknown specification type: {spec_type}")

        relative_path = self._spec_map[spec_type]
        full_path = self.managed_path / relative_path

        if not full_path.exists():
            raise FileNotFoundError(f"Specification not found: {full_path}")

        content = full_path.read_text(encoding="utf-8")
        file_hash = self._compute_hash(content)

        return {
            "spec_type": spec_type,
            "content": content,
            "hash": file_hash,
            "id": f"APX-{spec_type.upper()}-001",
            "version": "1.0.0",
            "file_path": str(relative_path),
            "read_at": _utcnow_z(),
        }

    def _get_previous_artifact_hash(self) -> Optional[str]:
        """Return the artifact_hash of the most recent artifact, or None if none exist."""
        files = sorted(
            self.artifacts_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not files:
            return None

        try:
            latest = json.loads(files[0].read_text(encoding="utf-8"))
            return latest.get("artifact_hash")
        except (json.JSONDecodeError, KeyError):
            return None

    def write_artifact(self, artifact: Dict[str, Any], name: str) -> Dict[str, Any]:
        """
        Write an artifact immutably with cryptographic chaining.

        Each write records the hash of the immediately preceding artifact,
        creating a verifiable, tamper-evident chain of all governed artifacts.

        Phase 2: Capability enforcement is expected to be performed by the caller
        (CapabilityChecker.require_capability("write_artifact")) before calling this method.
        """
        artifact_json = json.dumps(artifact, sort_keys=True)
        artifact_hash = self._compute_hash(artifact_json)

        timestamp = _utcnow_filename()
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).lower()
        filename = f"{safe_name}_{artifact_hash[:16]}_{timestamp}.json"
        full_path = self.artifacts_path / filename

        if full_path.exists():
            raise FileExistsError(f"Artifact already exists: {filename} (immutability violation)")

        previous_artifact_hash = self._get_previous_artifact_hash()

        wrapped = {
            "artifact": artifact,
            "written_by": "FileArtifactProvider",
            "written_at": _utcnow_z(),
            "artifact_hash": artifact_hash,
            "previous_artifact": previous_artifact_hash,
        }

        full_path.write_text(json.dumps(wrapped, indent=2, sort_keys=True), encoding="utf-8")

        return {
            "path": str(full_path.relative_to(self.base_path)),
            "absolute_path": str(full_path),
            "hash": artifact_hash,
            "written_at": wrapped["written_at"],
            "filename": filename,
            "previous_artifact": previous_artifact_hash,
        }

    def read_artifact(self, identifier: str) -> Dict[str, Any]:
        """Read an artifact by filename or hash prefix."""
        # Try exact filename first
        candidates = list(self.artifacts_path.glob(f"*{identifier}*.json"))
        if not candidates:
            raise FileNotFoundError(f"Artifact not found: {identifier}")

        # Take the most recent match
        full_path = max(candidates, key=lambda p: p.stat().st_mtime)
        content = full_path.read_text(encoding="utf-8")
        data = json.loads(content)

        # Integrity check
        stored_hash = data.get("artifact_hash")
        computed_hash = self._compute_hash(json.dumps(data["artifact"], sort_keys=True))
        if stored_hash and stored_hash != computed_hash:
            raise ValueError(f"Integrity check failed for {full_path.name}")

        data["read_at"] = _utcnow_z()
        return data

    def list_artifacts(self) -> list:
        files = sorted(
            self.artifacts_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return [f.name for f in files]

    def get_status(self) -> Dict[str, Any]:
        return {
            "provider": "FileArtifactProvider",
            "version": "0.2.0",
            "artifacts_count": len(self.list_artifacts()),
            "immutable": True,
        }


class SqliteArtifactProvider:
    """
    Phase 2 production provider backed by local SQLite + content-addressable blobs.

    Air-gapped compatible: stdlib sqlite3 only, all data on local disk.
    """

    def __init__(
        self,
        base_path: Optional[Path] = None,
        store: Optional["SqliteArtifactStore"] = None,
    ):
        from .store import SqliteArtifactStore as Store

        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.store = store or Store(self.base_path)
        self.managed_path = self.base_path / "managed"
        self.artifacts_path = self.managed_path / "artifacts"
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        self._spec_map = {
            "rule": "rules/rule1.md",
            "workflow": "workflows/workflow1.md",
            "knowledge": "knowledge/knowledge1.md",
        }

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _utcnow(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def read_specification(
        self,
        spec_type: str,
        *,
        require_approval: bool = True,
        governance_registry: Any = None,
    ) -> Dict[str, Any]:
        if require_approval and governance_registry is not None:
            governance_registry.require_approved_specs()

        if spec_type not in self._spec_map:
            raise ValueError(f"Unknown specification type: {spec_type}")

        relative_path = self._spec_map[spec_type]
        full_path = self.managed_path / relative_path
        if not full_path.exists():
            raise FileNotFoundError(f"Specification not found: {full_path}")

        content = full_path.read_text(encoding="utf-8")
        file_hash = self._compute_hash(content)

        id_line = next((line for line in content.splitlines() if "**ID:**" in line or "**Rule ID:**" in line), "")
        version_line = next((line for line in content.splitlines() if "Version" in line), "")

        spec_id = "APXV-RULE-001"
        if id_line:
            spec_id = id_line.split(":")[-1].strip().strip("*").strip()
        version = "1.0.0"
        if version_line:
            version = version_line.split(":")[-1].strip().strip("*").strip()

        return {
            "spec_type": spec_type,
            "content": content,
            "hash": file_hash,
            "id": spec_id,
            "version": version,
            "file_path": str(relative_path).replace("\\", "/"),
            "read_at": self._utcnow(),
        }

    def write_artifact(self, artifact: Dict[str, Any], name: str) -> Dict[str, Any]:
        meta = self.store.write_artifact(
            artifact=artifact,
            name=name,
            written_by="SqliteArtifactProvider",
        )
        self._mirror_to_legacy_path(artifact, meta, name)
        return meta

    def _mirror_to_legacy_path(
        self,
        artifact: Dict[str, Any],
        meta: Dict[str, Any],
        name: str,
    ) -> None:
        """Keep managed/artifacts/ mirror for backward-compatible tooling."""
        timestamp = datetime.now(timezone.utc).isoformat().replace(":", "-").replace(".", "-")
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).lower()
        filename = f"{safe_name}_{timestamp}.json"
        full_path = self.artifacts_path / filename
        wrapped = {
            "artifact": artifact,
            "written_by": "SqliteArtifactProvider",
            "written_at": meta["written_at"],
            "artifact_hash": meta["hash"],
            "previous_artifact": meta.get("previous_artifact"),
            "storage": "sqlite+cas",
            "store_path": meta["path"],
        }
        full_path.write_text(json.dumps(wrapped, indent=2, sort_keys=True), encoding="utf-8")
        meta["legacy_mirror"] = str(full_path.relative_to(self.base_path)).replace("\\", "/")

    def read_artifact(self, identifier: str) -> Dict[str, Any]:
        return self.store.read_artifact(identifier)

    def list_artifacts(self, name_prefix: Optional[str] = None) -> list:
        records = self.store.list_artifacts(name_prefix=name_prefix)
        return [r["blob_relpath"].split("/")[-1] for r in records]

    def find_latest_by_name(self, name_prefix: str) -> Optional[Dict[str, Any]]:
        records = self.store.list_artifacts(name_prefix=name_prefix, limit=1)
        if not records:
            return None
        return self.store.read_artifact(records[0]["artifact_hash"])

    def get_status(self) -> Dict[str, Any]:
        status = self.store.get_status()
        status["legacy_mirror_dir"] = str(self.artifacts_path.relative_to(self.base_path))
        return status
