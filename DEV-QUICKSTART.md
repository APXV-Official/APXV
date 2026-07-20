# Local development quickstart

Contributor loop for a full monorepo checkout (Windows, Linux, and macOS hosts).  
Operators should prefer desktop installers or [docs/QUICKSTART.md](docs/QUICKSTART.md).

Desktop packaging targets **Windows** (MSI/NSIS) and **Linux** (deb/AppImage); **macOS** DMG is a follow-up. See [ui/apps/desktop/README.md](ui/apps/desktop/README.md) and `scripts/build-desktop.sh` / release workflows.

---

## First-time runtime

```powershell
# Lighter (fast) — vendor ZK keys until sovereign bootstrap
py -3 -m scripts.setup_first_run --skip-zk

# Full sovereign (20–60 min first run)
# py -3 -m scripts.apxv_bootstrap --skip-ollama --skip-voice

python -m scripts.apxv_doctor
```

On Linux / macOS, use `python3` if `py` is not available.

Optional Proof Profile Groth16 keys:

```powershell
py -3 -m scripts.setup_universal_zk
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

Open http://127.0.0.1:5173 — paste operator key from `managed/config/OPERATOR-KEY-*.txt`.

| Area | Route (typical) |
|------|-----------------|
| Workbench | `/workshop` |
| Studio | `/studio` |
| Trust | `/trust` |
| Pack wizard (advanced) | `/packs?wizard=1` |

---

## Smoke

```powershell
python -m scripts.smoke_operator_flow
python -m scripts.apxv_demo --pack reference
```

---

## Docs

- [ui/docs/OPERATOR-GUIDE.md](ui/docs/OPERATOR-GUIDE.md)
- [docs/PROOF-STUDIO.md](docs/PROOF-STUDIO.md)
- [docs/MIGRATION-v1.5.md](docs/MIGRATION-v1.5.md)
- [CHANGELOG.md](CHANGELOG.md)
