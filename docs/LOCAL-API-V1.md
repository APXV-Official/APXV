# APXV — Local API v1 (historical)

> **Superseded.** Use [LOCAL-API-V2.md](LOCAL-API-V2.md) for the supported operator API (`/api/v2/*`). This page documents the pre-v1.4 v1 surface for migration reference only.

**Deployment:** Localhost only, air-gapped compatible  
**Dependencies:** Python stdlib only (no FastAPI, no cloud)

## Start Server

```bash
python -m scripts.apxv_serve
```

On first start, a default API key is generated and printed once. It is also written to `managed/config/OPERATOR-KEY-default-operator.txt` (v1.2.1+). Save it and delete the hint file after copying if desired.

Configuration: `managed/config/server.json`

```json
{
  "bind_address": "127.0.0.1",
  "port": 8741,
  "require_auth": true
}
```

## Authentication

All endpoints except `/health` require an API key:

```
Authorization: Bearer <your-api-key>
```

or

```
X-APX-API-Key: <your-api-key>
```

(`APXV-API-KEY` is the canonical header in v1.3.0+; legacy alias accepted.)

Keys are stored as SHA-256 hashes in `managed/config/api_keys.json`.

New keys created via `apxv_ctl api-key create` are accepted immediately without restarting `apxv_serve` (v1.2.1+).

## Health and status

`GET /health` (no auth) returns HTTP 200 with:

```json
{
  "status": "healthy",
  "air_gapped": true,
  "integrity": { "healthy": true, "audit_summary": {}, ... }
}
```

When audit logs fail verification, `status` is `degraded` (v1.2.1+) and the server keeps running — pipelines are not blocked by corrupt lines alone (v1.2.1+).

**v1.2.2+ diagnostics:** `integrity.audit_summary` lists each audit log with `chain_valid`, `corrupt_line_count`, `entry_count`, and `issue`:

| `issue` | Meaning | Typical recovery |
|---------|---------|------------------|
| `corrupt_lines` | Unparseable JSON in the log | Back up `managed/`, remove affected files under `managed/audit/`, run `setup_first_run` |
| `chain_break` | Valid JSON but hash chain broken | Remove `managed/audit/*.log`, run `setup_first_run` (or `fresh_reset`) |
| (absent) | Log healthy | No action |

`integrity.recovery_hints` duplicates actionable hints. Same classification appears in `python -m scripts.apxv_doctor` and `python -m scripts.apxv_ctl integrity` (supports `--base-path` for alternate instances).

See [RUNBOOKS/RUNBOOK-UPGRADE.md](../RUNBOOKS/RUNBOOK-UPGRADE.md) for upgrade-specific context.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Store + audit integrity check |
| GET | `/status` | Yes | Full runtime status |
| GET | `/governance` | Yes | Active governance specifications |
| GET | `/capabilities` | Yes | Signed capability policy status |
| GET | `/backups` | Yes | List local backup archives |
| POST | `/backup/create` | Yes | Create backup of `managed/` + ZK key directories |
| POST | `/backup/restore` | Yes | Restore from backup filename in `managed/backups/` |
| POST | `/pipeline/run` | Yes | Run or queue pipeline |
| GET | `/jobs` | Yes | List recent jobs |
| GET | `/jobs/{id}` | Yes | Job status and result |
| GET | `/artifacts/{id}` | Yes | Read artifact by hash/id |

## Run Pipeline

**Async (default)** — returns job ID immediately:

```bash
curl -X POST http://127.0.0.1:8741/pipeline/run \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Contact john@example.com", "attest": true, "async": true}'
```

**Sync** — waits for completion:

```bash
curl -X POST http://127.0.0.1:8741/pipeline/run \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Contact john@example.com", "attest": false, "async": false}'
```

## Job Queue

Jobs are persisted in `managed/store/apxv.db` (legacy `apx.db` opened if present). Failed jobs retry once by default.

Poll job status:

```bash
curl http://127.0.0.1:8741/jobs/job-abc123 \
  -H "Authorization: Bearer YOUR_KEY"
```