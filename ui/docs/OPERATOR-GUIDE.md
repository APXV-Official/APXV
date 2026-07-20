# APXV — Operator Guide

**Version:** 1.5.0 · **API:** v2 (`127.0.0.1:8741`)

Local operator console for governed agent pipelines — browser UI or Tauri desktop app.  
**Product loop:** Studio (author) → Workbench (assemble & run) → Runs / Artifacts → Trust.

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

1. Install from [GitHub Releases (latest)](https://github.com/APXV-Official/APXV/releases/latest).
2. Launch APXV — **bootstrap wizard** runs sovereign ZK setup (20–60 min typical).
3. Confirm operator key on the setup screen.
4. Open **System** and confirm health / sovereign status.

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

## Console map

| Nav | Purpose |
|-----|---------|
| **Workbench** | Freeform board: shelf blocks, optional wires, proof bind, **Run** |
| **Studio** | Author **Agents**, **Packs**, and **Proof Profiles** — Save → Test → Promote |
| **Runs** | Job queue, live updates, human approval, proof claims |
| **Artifacts** | Stored outputs, reports, redactions, ZK material |
| **Trust** | Hub for **Verify**, **Audit**, and **Governance** |
| **System** | Doctor, integrity, backups, integrations |
| **Settings** | API key, models, repair integrations, verifier export |

Keyboard: **Ctrl/⌘+K** opens the command palette.

## 5-minute happy path

1. Connect with your operator API key.
2. On **Workbench**, open the pipeline library or drop packs/agents from the shelf.
3. **Run** — review live step status; open **Last job** under **Runs**.
4. In **Studio → Proofs**, create a profile (template or predicates) → Save → Test → Promote.
5. On **Workbench → Proofs**, bind the profile, Save, Run.
6. Confirm the claim on **Runs** detail; optionally open **Trust → Verify**.

Details: [PROOF-STUDIO.md](../../docs/PROOF-STUDIO.md)

## Building blocks

| Block | Author in | Use on |
|-------|-----------|--------|
| **Agent** | Studio → Agents | Workbench shelf |
| **Pack** | Studio → Packs (or advanced `/packs?wizard=1`) | Workbench shelf |
| **Proof Profile** | Studio → Proofs | Workbench → bind → Run |

Tutorial: [BUILD-YOUR-FIRST-PACK.md](../../docs/BUILD-YOUR-FIRST-PACK.md) · Catalog: [PACK-CATALOG.md](../../docs/PACK-CATALOG.md)

### Studio promote

Promote unlocks after a successful **Test**. If promotion is rejected, the console may offer an operator **Force promote** override.

### Health banner

| Status | Meaning |
|--------|---------|
| Not connected | Add key in Settings / Connect |
| Runtime unavailable | Start `apxv_serve` (or desktop **Start server**) |
| Vendor keys (degraded) | Store/audit OK; run `python -m scripts.apxv_bootstrap` once for sovereign keys |
| Integrity issues | **System** → doctor / repair |

Vendor keys are safe to operate; proofs work but are not operator-sovereign until bootstrap.

## Daily operations

| Task | Where |
|------|--------|
| Assemble and run a pipeline | **Workbench** |
| Author agent / pack / proof | **Studio** |
| Monitor jobs / approve pause | **Runs** |
| Inspect outputs + ZK | **Artifacts** or **Runs → detail** |
| Verify attestation | **Trust → Verify** |
| Audit chain | **Trust → Audit** |
| Rules / workflows / proposals | **Trust → Governance** |
| Doctor / backups | **System** |
| Keys / models / desktop server | **Settings** |

## Advanced pack wizard

Day-to-day authoring is **Studio**. The five-step pack wizard remains at `/packs?wizard=1` (command palette: **Advanced pack wizard**).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| 401 Unauthorized | Re-run onboarding in **Settings**; confirm key in `api_keys.json` |
| Cannot reach runtime | Start `apxv_serve` or relaunch the desktop app |
| Start server does nothing (Windows desktop) | Install Python 3.10+ from python.org; **Settings → Runtime process** |
| Vendor keys banner | Run bootstrap from the install root; restart the API |
| Promote disabled | Complete **Test (runtime)** first |
| Proof claim failed | Fail-closed by design — adjust predicates or input |
| Jobs list empty | Confirm API is running; **Refresh** in the header |
| AI pack / Ollama | **Settings → Repair integrations** |

Include `python -m scripts.apxv_doctor` output in [GitHub Issues](https://github.com/APXV-Official/APXV/issues).

## Export verifier bundle

**Settings → Download verifier bundle** exports JSON for offline attestation verification (VKs from **your** sovereign setup when bootstrapped).

## E2E tests (developers)

With runtime and UI running, set `APXV_API_KEY` to a valid operator key:

```powershell
cd ui/apps/web
pnpm exec playwright test e2e/endgame-full.spec.ts
```

## Clean demo instance

To reset Studio drafts after heavy testing, see [CLEAN-DEMO-INSTANCE.md](../../docs/CLEAN-DEMO-INSTANCE.md).
