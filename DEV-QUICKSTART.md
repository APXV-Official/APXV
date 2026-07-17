# Developer quickstart

Contributor loop for a local monorepo checkout of APXV. For operator install paths, see [docs/QUICKSTART.md](docs/QUICKSTART.md) and [docs/INSTALL-USER.md](docs/INSTALL-USER.md).

---

## First-time runtime (sovereign bootstrap)

From the repository root:

```powershell
# Native sovereign path (20–60 min first run)
.\scripts\install-full.ps1
```

Prefer a fresh bootstrap when changing entity circuit sets. Upgrading an existing install: [docs/MIGRATION-v1.4.md](docs/MIGRATION-v1.4.md).

```powershell
python -m scripts.apxv_doctor
python -m scripts.apxv_ctl integrity
```

---

## Daily dev loop

**Terminal 1 — API**

```powershell
python -m scripts.apxv_serve
```

**Terminal 2 — Operator UI**

```powershell
cd ui
pnpm install
pnpm dev
```

Open http://localhost:5173 — operator key from `managed/config/OPERATOR-KEY-*.txt`.

---

## Tests

```powershell
python -m pytest
cd ui
pnpm --filter @apxv/web test:e2e
```

**Desktop** (Windows / Linux / macOS — see `ui/apps/desktop/README.md`):

```powershell
# Windows
.\scripts\build-desktop.ps1
# or: .\scripts\tauri-smoke.ps1

# Linux / macOS
./scripts/build-desktop.sh
```

---

## Useful checks

```powershell
python -m scripts.apxv_demo --pack reference
python -m scripts.verify_attestation --real-zk <path-to-latest-artifact.json>
python -m pytest tests/ -k "api" -q
```

---

## Website preview

```powershell
cd website
.\preview.ps1
```

Opens http://127.0.0.1:5500/
