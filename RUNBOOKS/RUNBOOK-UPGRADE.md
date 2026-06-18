# APX v1 — Runbook: Upgrade & Rollback

**Purpose:** Safe upgrade and rollback procedures for an APX v1 deployment.

---

## 1. Pre-Upgrade Checklist

Before performing any upgrade:

1. **Backup the entire `managed/` directory**
   - This includes artifacts, audit logs, and verification keys (`managed/keys/`).
   - Store the backup in a secure, separate location.

2. **Verify current system health**
   - Run `AuditLogger.verify_chain()` on all audit logs.
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
docker-compose down
```

### 2.3 Start with New Image

```bash
docker-compose up -d --build
```

### 2.4 Post-Upgrade Verification

- Check logs for successful startup
- Run `AuditLogger.verify_chain()` again
- Verify recent artifacts are still readable
- Test a small end-to-end attestation flow

---

## 3. Upgrade Procedure (Python / Source)

1. Backup `managed/`
2. Pull latest code or new package version
3. Reinstall:
   ```bash
   pip install -e . --upgrade
   ```
4. Restart the application
5. Verify as above

---

## 4. Rollback Procedure

If the upgrade causes issues:

1. Stop the current deployment
2. Restore the `managed/` directory from the pre-upgrade backup (if needed)
3. Redeploy the previous known-good version:
   ```bash
   docker-compose down
   docker-compose up -d -f docker-compose.yml
   # (or use previous image tag)
   ```
4. Verify audit log and artifact chain integrity
5. Confirm system functionality with a test run

---

## 5. Data Migration Notes

- APX v1 currently uses file-based storage under `managed/`
- Most upgrades should not require data migration
- If a future version introduces breaking changes to artifact or log formats, migration steps will be documented in the release notes

---

## 6. Best Practices

- Always test upgrades in a staging environment first
- Keep at least one previous version’s image available for quick rollback
- Maintain regular backups of `managed/keys/` (verification keys)
- Document every upgrade with date, version, and any issues encountered

---

*Last updated: 2026-06-10*