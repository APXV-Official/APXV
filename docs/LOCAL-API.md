# APX v1 — Local API Server

**Deployment:** Localhost only, air-gapped compatible  
**Dependencies:** Python stdlib only (no FastAPI, no cloud)

## Start Server

```bash
python -m scripts.apx_serve
```

On first start, a default API key is generated and printed once. Save it.

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

Keys are stored as SHA-256 hashes in `managed/config/api_keys.json`.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Store + audit integrity check |
| GET | `/status` | Yes | Full runtime status |
| GET | `/governance` | Yes | Active governance specifications |
| GET | `/capabilities` | Yes | Signed capability policy status |
| GET | `/backups` | Yes | List local backup archives |
| POST | `/backup/create` | Yes | Create backup of `managed/` + `rust/keys/` |
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

Jobs are persisted in `managed/store/jobs.db`. Failed jobs retry once by default.

Poll job status:

```bash
curl http://127.0.0.1:8741/jobs/job-abc123 \
  -H "Authorization: Bearer YOUR_KEY"
```