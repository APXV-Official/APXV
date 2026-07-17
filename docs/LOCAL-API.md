# APXV — Local HTTP API

APXV exposes a localhost-only HTTP API on port **8741** (default). Start with:

```bash
python -m scripts.apxv_serve
```

## Contract

| Version | Doc | Base path | Status |
|---------|-----|-----------|--------|
| **v2** (primary) | [LOCAL-API-V2.md](LOCAL-API-V2.md) | `/api/v2/*` | Operator console, Pack Studio, desktop app |

Use **API v2** for all new integrations. Authentication: `APXV-API-KEY` header (or `Authorization: Bearer <key>`). For upgrades from older clients, the header `X-APX-API-Key` is still accepted.

## Quick links

- OpenAPI contract: `ui/openapi/apxv-api-v2.yaml` (when present)
- Operator guide: [ui/docs/OPERATOR-GUIDE.md](../ui/docs/OPERATOR-GUIDE.md)
- Upgrade from v1.3.x: [MIGRATION-v1.4.md](MIGRATION-v1.4.md)
- Upgrade from v1.2.x: [MIGRATION-v1.3.md](MIGRATION-v1.3.md)
