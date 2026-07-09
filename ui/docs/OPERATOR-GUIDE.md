# APXV — Operator Guide

**Version:** 1.3.0 · **API:** v2 (`127.0.0.1:8741`)

Local operator console for governed agent pipelines — browser UI or Tauri desktop app. Every action maps to a documented REST endpoint.

## Install surfaces

| Surface | How to start |
|---------|--------------|
| **Desktop app** | [INSTALL-USER.md](../../docs/INSTALL-USER.md) — MSI (Windows) or deb/AppImage (Linux); first launch runs sovereign bootstrap |
| **Browser UI (dev)** | `python -m scripts.apxv_serve` + `cd ui && pnpm dev` → http://127.0.0.1:5173 |
| **Docker + UI** | `docker compose -f docker-compose.yml -f docker-compose.ui.yml up -d` → :5173 + :8741 |

Sovereign trust: [SOVEREIGN-SETUP.md](../../docs/SOVEREIGN-SETUP.md)

## Quick start (browser dev)

From the repository root:

```powershell
# Terminal 1 — runtime
python -m scripts.apxv_serve

# Terminal 2 — UI
cd ui
pnpm dev
```

Open http://127.0.0.1:5173 and complete onboarding with your operator API key from `managed/config/OPERATOR-KEY-*.txt`.

## First launch (desktop)

1. Install from [GitHub Releases](https://github.com/APXV-Official/APXV/releases).
2. Launch APXV — **bootstrap wizard** runs sovereign ZK setup (20–60 min typical).
3. Confirm operator key on the setup screen.
4. Dashboard — verify `sovereign_setup` badge on **System**.

## Authentication

All v2 endpoints (except `GET /api/v2/system/health`) require an operator key:

```
Authorization: Bearer <api-key>
```

or:

```
APXV-API-KEY: <api-key>
```

Keys are stored in `managed/config/api_keys.json`. The UI saves your key locally after onboarding.

## Daily operations

| Task | Where |
|------|--------|
| Run a governed pipeline | **Pipeline** or **Dashboard → Quick run** |
| Monitor job progress | **Jobs** (live SSE updates) |
| Inspect redactions + ZK proofs | **Jobs → detail** or **Artifacts → Open** |
| Independently verify attestation | **Verify** or artifact **Verify** tab |
| Review audit chain | **Audit** |
| Change rules/workflows/knowledge | **Governance** (propose → approve → apply) |
| Doctor / integrity / backups | **System** |
| Ollama / voice repair | **Settings → Repair integrations** |
| Create or revoke API keys | **Settings** |

## Agent packs

1. **Agent packs** → **Create pack** (reference or minimal template).
2. Edit pipeline logic on disk:
   `governance-libraries/apxv-pack-<slug>/agents/custom_agents.py`
3. Implement `run_pack_pipeline(input_text, runtime, **kwargs)`.
4. Run via **Run pack (sample input)** or **Pipeline** with the pack selected.

Pack governance files are scaffolded under each pack's `governance/` folder. Apply changes through **Governance studio** or `python -m scripts.apxv_ctl`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| 401 Unauthorized | Re-run onboarding in **Settings**; confirm key in `api_keys.json` |
| Cannot reach runtime | Start `apxv_serve` or relaunch desktop app |
| Doctor integrity fail | **System → Repair audit chain**; check sovereign status |
| `sovereign_setup: false` | Re-run bootstrap — [SOVEREIGN-SETUP.md](../../docs/SOVEREIGN-SETUP.md) |
| AI pack unavailable | Install Ollama; **Settings → Repair integrations** |
| Jobs list empty | Confirm API is running; click **Refresh all** in the header |

Include `python -m scripts.apxv_doctor` output in [GitHub Issues](https://github.com/APXV-Official/APXV/issues).

## Export verifier bundle

**Settings → Download verifier bundle** exports JSON for offline attestation verification (VKs from **your** sovereign setup).

## E2E tests (developers)

With runtime and UI running:

```powershell
cd ui
pnpm test:e2e
```

Set `APXV_API_KEY` if not using the default operator key.