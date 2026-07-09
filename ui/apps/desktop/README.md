# APXV — Desktop (Tauri)

Tauri 2 desktop app. First launch runs the **sovereign bootstrap wizard**, then setup, then the dashboard.

**Operator data root (v1.3):**

| OS | Path |
|----|------|
| Windows | `%LOCALAPPDATA%\APXV\` |
| macOS | `~/Library/Application Support/APXV/` |
| Linux | `$XDG_DATA_HOME/APXV` or `~/.local/share/APXV/` |

## Features

- First-run **Bootstrap** wizard (ZK setup, optional Ollama/Vosk)
- Auto-start API after sovereign bootstrap
- **Setup** screen (operator key + paste once)
- System tray — left-click or **Open APXV** to restore; **Quit** stops API and exits
- Single instance — second launch focuses the running window
- Close window → minimizes to tray (API keeps running)

## Development

From the repo root:

```powershell
cd ui\apps\desktop
pnpm dev
```

## Production build

v1.3.1 ships **Windows MSI/NSIS** and **Linux deb/AppImage**. macOS DMG is planned for a follow-up release (build requires a Mac).

### Windows

From the repo root:

```powershell
.\scripts\build-desktop.ps1
```

Outputs:

- `ui\apps\desktop\src-tauri\target\release\apxv.exe`
- `ui\apps\desktop\src-tauri\target\release\bundle\msi\APXV_1.3.1_x64_en-US.msi`
- `ui\apps\desktop\src-tauri\target\release\bundle\nsis\APXV_1.3.1_x64-setup.exe`

### macOS / Linux

```bash
chmod +x scripts/*.sh
./scripts/build-desktop.sh
```

Outputs (platform-dependent):

- macOS: `bundle/macos/APXV.app`, `bundle/dmg/*.dmg`
- Linux: `bundle/deb/*.deb`, `bundle/appimage/*.AppImage`

**Prerequisites:** Python 3.9+, Node 20+, pnpm 9+, Rust stable. Linux builds need `webkit2gtk` and related Tauri deps per [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/).

### App icon

Source: `src-tauri/icons/app-icon.svg` (site colors `#10141c`, white **APXV**).

Regenerate platform icons after editing the SVG:

```powershell
cd ui\apps\desktop
pnpm exec tauri icon src-tauri/icons/app-icon.svg -o src-tauri/icons
```

## Smoke test

Windows:

```powershell
.\scripts\tauri-smoke.ps1
```

macOS / Linux:

```bash
./scripts/tauri-smoke.sh
```

Gate: `cargo check`, cross-platform path resolution, `python_cmd.rs`, `tauri_smoke.py`, Playwright bootstrap preview.

Debug builds auto-detect the repo runtime tree, or set `APXV_DEV_ROOT` / `APXV_ROOT`.