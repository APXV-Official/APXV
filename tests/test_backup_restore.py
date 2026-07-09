"""Tests for backup and restore (Phase 4 Step 4)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.backup_restore import BackupManager, BackupRestoreError, MANIFEST_NAME


def _seed_env(base: Path) -> None:
    managed = base / "managed"
    (managed / "config").mkdir(parents=True)
    (managed / "rules").mkdir(parents=True)
    (managed / "store").mkdir(parents=True)
    (managed / "config" / "server.json").write_text('{"port": 8741}', encoding="utf-8")
    (managed / "rules" / "rule1.md").write_text("# test rule\n", encoding="utf-8")

    keys = base / "rust" / "apxv-circuits" / "keys"
    keys.mkdir(parents=True)
    (keys / "manifest.json").write_text('{"circuits": {}}', encoding="utf-8")
    (keys / "redaction.vk").write_bytes(b"vk-bytes")

    entity_keys = base / "rust" / "apxv-zk" / "keys"
    entity_keys.mkdir(parents=True)
    (entity_keys / "entity-manifest.json").write_text('{"circuits": {}}', encoding="utf-8")


@pytest.fixture
def backup_env(tmp_path):
    _seed_env(tmp_path)
    return tmp_path, BackupManager(tmp_path)


def test_create_and_verify_backup(backup_env):
    base, manager = backup_env
    result = manager.create_backup()
    archive = Path(result["path"])
    assert archive.exists()

    verification = manager.verify_backup(archive)
    assert verification["valid"] is True
    assert verification["file_count"] >= 3


def test_manifest_lists_managed_and_rust_keys(backup_env):
    base, manager = backup_env
    archive = Path(manager.create_backup()["path"])
    manifest = manager.read_manifest(archive)
    paths = {entry["path"] for entry in manifest["files"]}
    assert "managed/config/server.json" in paths
    assert "managed/rules/rule1.md" in paths
    assert "rust/apxv-circuits/keys/manifest.json" in paths
    assert "rust/apxv-circuits/keys/redaction.vk" in paths
    assert "rust/apxv-zk/keys/entity-manifest.json" in paths
    assert not any("managed/backups/" in p for p in paths)


def test_restore_roundtrip(backup_env):
    base, manager = backup_env
    rule_path = base / "managed" / "rules" / "rule1.md"
    rule_path.write_text("# original\n", encoding="utf-8")

    archive = Path(manager.create_backup()["path"])
    rule_path.write_text("# tampered\n", encoding="utf-8")
    (base / "managed" / "config" / "server.json").write_text('{"port": 9999}', encoding="utf-8")

    restored = manager.restore_backup(archive, create_safety_backup=False)
    assert restored["restored_file_count"] >= 3
    assert rule_path.read_text(encoding="utf-8") == "# original\n"
    assert json.loads((base / "managed" / "config" / "server.json").read_text())["port"] == 8741


def test_verify_detects_tampered_archive(backup_env, tmp_path):
    _, manager = backup_env
    archive = Path(manager.create_backup()["path"])

    import tarfile

    tampered = tmp_path / "tampered.tar.gz"
    with tarfile.open(archive, "r:gz") as src, tarfile.open(tampered, "w:gz") as dst:
        for member in src.getmembers():
            data = src.extractfile(member)
            if member.name == "managed/rules/rule1.md" and data is not None:
                payload = b"# changed\n"
                member.size = len(payload)
                dst.addfile(member, fileobj=_bytes_buffer(payload))
            elif data is not None:
                dst.addfile(member, fileobj=data)

    verification = manager.verify_backup(tampered)
    assert verification["valid"] is False
    assert any("Hash mismatch" in issue for issue in verification["issues"])


def test_restore_rejects_invalid_backup(backup_env, tmp_path):
    _, manager = backup_env
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(b"not a tar file")
    with pytest.raises(BackupRestoreError):
        manager.restore_backup(bad, create_safety_backup=False)


def test_list_backups(backup_env):
    _, manager = backup_env
    manager.create_backup()
    backups = manager.list_backups()
    assert len(backups) == 1
    assert backups[0]["valid"] is True


class _bytes_buffer:
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