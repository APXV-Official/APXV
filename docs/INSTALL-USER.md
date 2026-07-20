# Install APXV — desktop app (operators)

Download-and-run APXV for individual operators. No git clone required.

**v1.5.0 ships:** Windows MSI/NSIS and Linux deb/AppImage. macOS DMG is planned for a follow-up release.

## Download

Get installers from **[GitHub Releases (latest)](https://github.com/APXV-Official/APXV/releases/latest)** — see also [DOWNLOADS.md](DOWNLOADS.md).

Artifact names follow `APXV_<version>_…` (example for v1.5.0 below). Always prefer **latest** on the release page.

| Platform | Artifact (v1.5.0 example) | Notes |
|----------|---------------------------|-------|
| **Windows 10/11** | `APXV_1.5.0_x64_en-US.msi` or `APXV_1.5.0_x64-setup.exe` | Requires Python 3.10+ on the machine (desktop resolves real interpreter path) |
| **Linux (amd64)** | `APXV_1.5.0_amd64.deb` or `APXV_1.5.0_amd64.AppImage` | Debian/Ubuntu: `.deb`; portable: AppImage. GTK/WebKit deps per [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/) |
| **macOS** | DMG (planned) | Build requires a Mac; not in current launch set |

For teams without a desktop install, use [DOCKER.md](DOCKER.md) instead.

## Install steps

### Windows

1. Download the MSI or NSIS installer from Releases.
2. Run the installer (standard per-user or per-machine install).
3. Launch **APXV™** from the Start Menu.
4. Complete the **bootstrap wizard** on first launch (sovereign ZK setup — see [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md)).
5. Paste or confirm your operator API key on the setup screen (auto-discovery of `OPERATOR-KEY-*.txt` when present).
6. Open **Workbench** (home), **Studio** for Agents/Packs/Proof Profiles, **Runs**, and **Trust**. Advanced pack wizard remains at `/packs?wizard=1`.

### Linux

**Debian/Ubuntu (.deb):**

```bash
sudo dpkg -i APXV_1.5.0_amd64.deb
sudo apt install -f   # if dependencies are missing
apxv   # or find APXV in your application menu
```

**AppImage:**

```bash
chmod +x APXV_1.5.0_amd64.AppImage
./APXV_1.5.0_amd64.AppImage
```

Then follow the same first-launch bootstrap wizard as Windows.

## Where data lives

| OS | Operator data root |
|----|-------------------|
| Windows | `%LOCALAPPDATA%\APXV\` |
| Linux | `$XDG_DATA_HOME/APXV` or `~/.local/share/APXV/` |
| macOS (future) | `~/Library/Application Support/APXV/` |

Contains `managed/`, ZK keys, runtime payload, and `install.json`. **Back this up** — see [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md#backup-required).

## First launch (what to expect)

| Phase | Typical duration |
|-------|------------------|
| Sovereign ZK setup (3 governance + 6 entity circuits) | 20–60 min typical (faster on well-provisioned hardware) |
| Optional Ollama model pull | 5–30 min |
| Optional Vosk download | ~1 min |
| First attest + verify smoke | 1–2 min |

The wizard shows progress. You can skip Ollama/Vosk and repair integrations later from **Settings**.

Success criteria:

- Dashboard shows healthy runtime
- `install.json` has `"sovereign_setup": true` and `"bootstrap_version": "1.4.0"` (or later)
- A sample pipeline reaches `ATTESTED` and verify passes

## Upgrading from v1.3.x

See [MIGRATION-v1.4.md](MIGRATION-v1.4.md). Highlights:

- Install the v1.4 desktop build; quit the app fully before upgrading
- `normalization` / `threat` are no longer default entity circuits — migrate `install.json` if doctor reports VK mismatches
- Prefer governance edits via Pack Studio / Governance studio (not hand-editing approved rule files)

## Daily use

- **System tray** — APXV keeps the API running; close window minimizes to tray
- **Open APXV** — restore the window from tray or launcher
- **Quit** — stops API and exits (use tray Quit, not force-kill)
- **Settings → Runtime process** — Start / Stop / Restart server (desktop only; resolves your real install folder automatically)
- **Pack Studio** — wizard at **Build your pipeline** or `/packs?wizard=1`

Same features as the browser UI: Dashboard, Pipeline, Jobs, Artifacts (Report tab), Verify, Audit, Governance, Agent packs, Settings.

Operator guide: [ui/docs/OPERATOR-GUIDE.md](../ui/docs/OPERATOR-GUIDE.md).

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Bootstrap fails on ZK | Ensure Python 3.9+ and disk space; check wizard log; run `apxv_doctor` from Settings |
| Port 8741 in use | Quit other APXV/Docker instances; **Settings → Restart server** (desktop) |
| Runtime **degraded** / Integrity **Issues** | Run doctor; if audit chain break, quit app and run `python -m scripts.repair_integrity --all` from the install root |
| Start server does nothing (Windows) | Install Python 3.10+ from python.org; Settings shows error text when spawn fails |
| AI pack unavailable | Install Ollama on host; **Settings → Repair integrations** |
| Voice unavailable | Run voice repair or bootstrap with Vosk enabled |

Include `python -m scripts.apxv_doctor` output when opening [GitHub Issues](https://github.com/APXV-Official/APXV/issues).

## Related

- [DOWNLOADS.md](DOWNLOADS.md) — installer index
- [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md) — trust and keys
- [MIGRATION-v1.4.md](MIGRATION-v1.4.md) — v1.3.x → v1.4.0
- [QUICKSTART.md](QUICKSTART.md) — native/dev path
