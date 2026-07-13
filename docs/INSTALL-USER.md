# Install APXV — desktop app (operators)

Download-and-run APXV for individual operators. No git clone required.

**v1.3.2 ships:** Windows MSI/NSIS and Linux deb/AppImage. macOS DMG is planned for a follow-up release.

## Download

Get installers from **[GitHub Releases (latest)](https://github.com/APXV-Official/APXV/releases/latest)** — see also [DOWNLOADS.md](DOWNLOADS.md).

Artifact names follow `APXV_<version>_…` (example for v1.3.2 below). Always prefer **latest** on the release page.

| Platform | Artifact (v1.3.2 example) | Notes |
|----------|---------------------------|-------|
| **Windows 10/11** | `APXV_1.3.2_x64_en-US.msi` or `APXV_1.3.2_x64-setup.exe` | Requires Python 3.9+ on the machine (embedded runtime invokes it) |
| **Linux (amd64)** | `APXV_1.3.2_amd64.deb` or `APXV_1.3.2_amd64.AppImage` | Debian/Ubuntu: `.deb`; portable: AppImage. GTK/WebKit deps per [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/) |
| **macOS** | DMG (planned) | Build requires a Mac; not in current launch set |

For teams without a desktop install, use [DOCKER.md](DOCKER.md) instead.

## Install steps

### Windows

1. Download the MSI or NSIS installer from Releases.
2. Run the installer (standard per-user or per-machine install).
3. Launch **APXV™** from the Start Menu.
4. Complete the **bootstrap wizard** on first launch (sovereign ZK setup — see [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md)).
5. Paste or confirm your operator API key on the setup screen (v1.3.2 can auto-discover `OPERATOR-KEY-*.txt`).
6. Use the dashboard — pipeline, jobs, verify, governance, packs.

### Linux

**Debian/Ubuntu (.deb):**

```bash
sudo dpkg -i APXV_1.3.2_amd64.deb
sudo apt install -f   # if dependencies are missing
apxv   # or find APXV in your application menu
```

**AppImage:**

```bash
chmod +x APXV_1.3.2_amd64.AppImage
./APXV_1.3.2_amd64.AppImage
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
| Sovereign ZK setup (11 circuits) | 20–60 min typical (faster on well-provisioned hardware) |
| Optional Ollama model pull | 5–30 min |
| Optional Vosk download | ~1 min |
| First attest + verify smoke | 1–2 min |

The wizard shows progress. You can skip Ollama/Vosk and repair integrations later from **Settings**.

Success criteria:

- Dashboard shows healthy runtime
- `install.json` has `"sovereign_setup": true`
- A sample pipeline reaches `ATTESTED` and verify passes

## Daily use

- **System tray** — APXV keeps the API running; close window minimizes to tray
- **Open APXV** — restore the window from tray or launcher
- **Quit** — stops API and exits (v1.3.2 kills process tree on quit)

Same features as the browser UI: Dashboard, Pipeline, Jobs, Artifacts (Report tab), Verify, Audit, Governance, Agent packs, Settings.

Operator guide: [ui/docs/OPERATOR-GUIDE.md](../ui/docs/OPERATOR-GUIDE.md).

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Bootstrap fails on ZK | Ensure Python 3.9+ and disk space; check wizard log; run `apxv_doctor` from Settings |
| Port 8741 in use | Quit other APXV/Docker instances; **Settings → Restart server** (desktop) |
| Linux job failed immediately | Use v1.3.2+ desktop build (Tauri HTTP for pipeline API) |
| AI pack unavailable | Install Ollama on host; **Settings → Repair integrations** |
| Voice unavailable | Run voice repair or bootstrap with Vosk enabled |

Include `python -m scripts.apxv_doctor` output when opening [GitHub Issues](https://github.com/APXV-Official/APXV/issues).

## Other install paths

| Audience | Path |
|----------|------|
| Developers / contributors | [QUICKSTART.md](QUICKSTART.md) — `install-full` |
| Teams / servers | [DOCKER.md](DOCKER.md) |
| Air-gapped | [AIR-GAP-INSTALL.md](AIR-GAP-INSTALL.md) |

Build installers from source: [ui/apps/desktop/README.md](../ui/apps/desktop/README.md).