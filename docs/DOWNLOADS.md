# Download APXV™

**Canonical installers:** [GitHub Releases (latest)](https://github.com/APXV-Official/APXV/releases/latest)

All desktop builds are published on the APXV-Official/APXV release page. Use that URL everywhere — README, website, and this doc link to the same place.

## Desktop installers

| Platform | File pattern | Install guide |
|----------|--------------|---------------|
| **Windows 10/11 (x64)** | `APXV_*_x64_en-US.msi` or `APXV_*_x64-setup.exe` | [INSTALL-USER.md](INSTALL-USER.md) |
| **Linux amd64** | `APXV_*_amd64.deb` or `APXV_*_amd64.AppImage` | [INSTALL-USER.md](INSTALL-USER.md) |
| **macOS** | DMG (planned) | — |

After install: complete **sovereign bootstrap** on first launch, then connect with your operator API key. See [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md).

## Other install paths

| Path | Audience | Link |
|------|----------|------|
| **Docker** | Teams, no local Rust | [DOCKER.md](DOCKER.md) |
| **Native / dev** | Contributors | [BUILDING.md](BUILDING.md) · `install-full` scripts |

## Verify downloads

Release assets are built by the **Release Desktop** GitHub Actions workflow. Checksums and signing notes are listed on each [release](https://github.com/APXV-Official/APXV/releases) when published.

For support: open a [GitHub Issue](https://github.com/APXV-Official/APXV/issues) with `python -m scripts.apxv_doctor` output.