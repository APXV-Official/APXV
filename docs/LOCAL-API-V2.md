# APXV — Local API v2

**Deployment:** Localhost only, air-gapped compatible  
**Base path:** `/api/v2/`  
**Contract:** `ui/openapi/apxv-api-v2.yaml`

Legacy v1 paths (`/health`, `/pipeline/run`, etc.) remain available.

## Authentication

All v2 endpoints except `GET /api/v2/system/health` require:

```
Authorization: Bearer <api-key>
```

or:

```
APXV-API-KEY: <api-key>
```

(`X-APX-API-Key` is accepted as a legacy alias.)

## Error envelope

```json
{
  "error": "code",
  "message": "Human-readable message",
  "details": {}
}
```

Every JSON response includes `X-Request-Id`.

## Pagination

List endpoints return:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

## System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/system/health` | Health + integrity (no auth) |
| GET | `/api/v2/system/status` | Full runtime status |
| GET | `/api/v2/system/doctor` | Doctor checks (`?check_llm=true`) |
| POST | `/api/v2/system/integrity` | Run integrity check |

## Artifacts

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/artifacts` | Paginated artifact index |
| GET | `/api/v2/artifacts/{hash}` | Full artifact payload |
| GET | `/api/v2/artifacts/{hash}/summary` | Card-friendly summary |

## Audit

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/audit/logs` | Log files + chain validity |
| GET | `/api/v2/audit/logs/{name}/entries` | Paginated log entries |

## Jobs & pipeline

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/jobs` | Paginated jobs (`?status=`) |
| GET | `/api/v2/jobs/{id}` | Job detail |
| GET | `/api/v2/jobs/stream` | SSE job updates (`?seconds=30`) |
| POST | `/api/v2/pipeline/run` | Pack-aware pipeline |

### Pipeline body

```json
{
  "pack": "reference",
  "input_text": "Contact john@example.com",
  "upload_id": "upload-abc",
  "attest": false,
  "async": true,
  "llm": {
    "backend": "simulated",
    "model": "qwen2.5:latest",
    "max_latency_ms": 120000
  }
}
```

Packs: `reference`, `document`, `ai`. Document pack requires `upload_id` from uploads API.

## Uploads

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/uploads` | `multipart/form-data` — `.txt`/`.json` |
| GET | `/api/v2/uploads/{id}` | Upload session metadata |
| DELETE | `/api/v2/uploads/{id}` | Delete session |

## Trust

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/verify/attestation` | Verify by `artifact_hash` or inline `attestation` |

```json
{
  "artifact_hash": "...",
  "real_zk": false
}
```

## Governance, backups, keys

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/packs` | Official pack catalog |
| GET | `/api/v2/packs/{id}` | Pack detail |
| GET | `/api/v2/governance/specs` | Active specs + content |
| GET/POST | `/api/v2/governance/proposals` | Proposal workflow |
| POST | `/api/v2/governance/proposals/{id}/{approve\|reject\|apply}` | Actions |
| GET | `/api/v2/capabilities` | Capability policy |
| GET/POST | `/api/v2/backups` | Backup list / create |
| POST | `/api/v2/backups/restore` | Restore archive |
| GET/POST | `/api/v2/keys` | List / create API keys |
| DELETE | `/api/v2/keys/{id}` | Revoke key (not last key) |

## Integrations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/integrations/ollama` | Local Ollama status + models |

## Start server

```bash
python -m scripts.apxv_serve
```

Operator UI (dev):

```bash
cd ui && pnpm dev
```

Vite proxies `/api` → `127.0.0.1:8741`.