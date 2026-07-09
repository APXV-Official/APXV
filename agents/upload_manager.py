"""Local multipart upload sessions for document pack ingest."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re
import uuid

SUPPORTED_SUFFIXES = frozenset({".txt", ".json"})


class UploadManager:
    """Stores batch upload files under managed/uploads/<session_id>/."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.root = self.base_path / "managed" / "uploads"
        self.root.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, upload_id: str) -> Path:
        safe = Path(upload_id).name
        return self.root / safe

    def _meta_path(self, upload_id: str) -> Path:
        return self._session_dir(upload_id) / "session.json"

    def create_session(self, *, label: str = "") -> Dict[str, Any]:
        upload_id = f"upload-{uuid.uuid4().hex[:16]}"
        session_dir = self._session_dir(upload_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "upload_id": upload_id,
            "label": label,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": [],
            "batch_dir": str(session_dir.relative_to(self.base_path)).replace("\\", "/"),
        }
        self._meta_path(upload_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta

    def get_session(self, upload_id: str) -> Optional[Dict[str, Any]]:
        meta_path = self._meta_path(upload_id)
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def add_files(self, upload_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        meta = self.get_session(upload_id)
        if not meta:
            raise FileNotFoundError(f"Upload session not found: {upload_id}")

        session_dir = self._session_dir(upload_id)
        saved: List[Dict[str, Any]] = []
        for item in files:
            filename = Path(item["filename"]).name
            suffix = Path(filename).suffix.lower()
            if suffix not in SUPPORTED_SUFFIXES:
                raise ValueError(f"Unsupported file type: {filename}")
            target = session_dir / filename
            target.write_bytes(item["content"])
            saved.append(
                {
                    "filename": filename,
                    "size_bytes": len(item["content"]),
                    "path": str(target.relative_to(self.base_path)).replace("\\", "/"),
                }
            )

        meta["files"].extend(saved)
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._meta_path(upload_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta

    def delete_session(self, upload_id: str) -> bool:
        session_dir = self._session_dir(upload_id)
        if not session_dir.exists():
            return False
        for path in sorted(session_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
        session_dir.rmdir()
        return True

    def batch_directory(self, upload_id: str) -> Path:
        meta = self.get_session(upload_id)
        if not meta or not meta.get("files"):
            raise ValueError(f"Upload session empty or missing: {upload_id}")
        return self._session_dir(upload_id)


def parse_multipart_form(body: bytes, content_type: str) -> Dict[str, Any]:
    """Parse multipart/form-data without external dependencies."""
    match = re.search(r"boundary=(?P<b>[^;]+)", content_type, re.I)
    if not match:
        raise ValueError("Missing multipart boundary")
    boundary = match.group("b").strip().strip('"')
    delimiter = ("--" + boundary).encode("utf-8")
    parts = body.split(delimiter)
    fields: Dict[str, str] = {}
    files: List[Dict[str, Any]] = []

    for part in parts:
        part = part.strip(b"\r\n-")
        if not part or part == b"--":
            continue
        header_blob, _, content = part.partition(b"\r\n\r\n")
        if not content:
            continue
        content = content.rstrip(b"\r\n")
        headers = header_blob.decode("utf-8", errors="replace")
        disposition = ""
        part_content_type = ""
        for line in headers.split("\r\n"):
            lower = line.lower()
            if lower.startswith("content-disposition:"):
                disposition = line.split(":", 1)[1].strip()
            elif lower.startswith("content-type:"):
                part_content_type = line.split(":", 1)[1].strip()

        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        if filename_match and filename_match.group(1):
            files.append(
                {
                    "field": name,
                    "filename": filename_match.group(1),
                    "content_type": part_content_type,
                    "content": content,
                }
            )
        else:
            fields[name] = content.decode("utf-8", errors="replace")

    return {"fields": fields, "files": files}