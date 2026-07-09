# APXV — Local HTTP API

APXV exposes a localhost-only HTTP API on port **8741** (default). Start with:

```bash
python -m scripts.apxv_serve
```

## Which contract to use

| Version | Doc | Base path | Status |
|---------|-----|-----------|--------|
| **v2** (primary) | [LOCAL-API-V2.md](LOCAL-API-V2.md) | `/api/v2/*` | Operator console + Pack Studio |
| **v1** (legacy) | [LOCAL-API-V1.md](LOCAL-API-V1.md) | `/health`, `/pipeline/run`, … | Deprecated — `Sunset: v1.4` |

New integrations should use **v2**. The v1 paths remain for backward compatibility through v1.3.x.

## Quick links

- OpenAPI contract: `ui/openapi/apxv-api-v2.yaml`
- Operator guide: `ui/docs/OPERATOR-GUIDE.md`
- Upgrade from v1.2.x: [MIGRATION-v1.3.md](MIGRATION-v1.3.md)