# APXV1 — Runbook: Upgrade & Rollback

**Purpose:** Safe upgrade and rollback procedures for an APXV1 deployment.

---

## 1. Pre-Upgrade Checklist

Before performing any upgrade:

1. **Backup the entire `managed/` directory**
   - This includes artifacts, audit logs, and verification keys (`managed/keys/`).
   - Store the backup in a secure, separate location.

2. **Verify current system health**
   - Run `python -m scripts.apx_doctor` (preferred) or `python -m scripts.apx_ctl integrity`.
   - Confirm all services/containers are running normally.

3. **Document the current version**
   - Note the current Docker image tag or Python package version.

---

## 2. Upgrade Procedure (Docker - Recommended)

### 2.1 Pull or Build New Image

```bash
docker pull your-registry/apx-v1:<new-version>
# or
docker build -t apx-v1:<new-version> .
```

### 2.2 Stop the Running Container

```bash
docker compose down
```

### 2.3 Start with New Image

```bash
docker compose up -d --build
```

Or use the one-command installer (removes stale `apx-v1` automatically since v1.2.2):

```powershell
.\scripts\install-docker.ps1
```

```bash
./scripts/install-docker.sh
```

### 2.4 Post-Upgrade Verification

- Check logs for successful startup
- Run `python -m scripts.apx_doctor`
- Verify recent artifacts are still readable
- Test a small end-to-end attestation flow (`apx_demo --pack reference`)

---

## 3. Upgrade Procedure (Python / Source)

1. Backup `managed/`
2. Pull latest code or new package version
3. Reinstall:
   ```bash
   pip install -e . --upgrade
   ```
4. Restart the application (`apx_serve` or Docker)
5. Verify as above

### 3.1 API key hint file (v1.2.0 → v1.2.2 in-place)

v1.2.1+ writes `managed/config/OPERATOR-KEY-default-operator.txt` on fresh setup. Upgraded trees may have `api_keys.json` only.

Create a new hint without server restart (hot-reload in v1.2.1+):

```bash
python -m scripts.apx_ctl api-key create my-app --save-hint --description "Post-upgrade"
```

Or run `python -m scripts.setup_first_run` — it prints an advisory if the default hint file is missing.

---

## 4. Degraded integrity after upgrade (v1.2.2+)

Long-lived `managed/` trees often show **NEEDS ATTENTION** while pipelines still work. Use per-log diagnostics from `apx_doctor`, `apx_ctl integrity`, or `GET /health`:

| Symptom | `issue` | Recovery |
|---------|---------|----------|
| Unparseable JSON lines | `corrupt_lines` | Back up `managed/`, remove affected files under `managed/audit/`, run `setup_first_run` |
| Valid JSON, broken hash chain | `chain_break` | Remove `managed/audit/*.log`, run `setup_first_run` — or `fresh_reset` for full local reset |
| All logs healthy | — | No action |

**Do not hand-edit audit log lines** — that breaks the hash chain.

Example chain-break (common on dev machines):

```
apx_ctl integrity
  system_audit.log: chain_break (0 corrupt lines, chain_valid=false)
  Recovery: Remove managed/audit/*.log and run setup_first_run
```

`/health` returns HTTP 200 with `"status": "degraded"` and `integrity.audit_summary` when audit logs fail verification.

---

## 5. Rollback Procedure

If the upgrade causes issues:

1. Stop the current deployment
2. Restore the `managed/` directory from the pre-upgrade backup (if needed)
3. Redeploy the previous known-good version:
   ```bash
   docker compose down
   docker compose up -d
   # (or use previous image tag)
   ```
4. Verify audit log and artifact chain integrity
5. Confirm system functionality with a test run

---

## 6. Data Migration Notes

- APXV1 currently uses file-based storage under `managed/`
- Most upgrades should not require data migration
- If a future version introduces breaking changes to artifact or log formats, migration steps will be documented in the release notes

---

## 7. Best Practices

- Always test upgrades in a staging environment first
- Keep at least one previous version's image available for quick rollback
- Maintain regular backups of `managed/keys/` (verification keys)
- Document every upgrade with date, version, and any issues encountered
- Use **fresh Docker volumes** for production — do not mount a polluted dev `managed/` folder (see [docs/DOCKER.md](../docs/DOCKER.md))

---

*Last updated: 2026-07-02*