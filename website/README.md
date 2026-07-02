# APXV marketing site

Static site deployed to **GitHub Pages** via `.github/workflows/pages.yml`.

**Current release on site:** v1.2.2 (eyebrow, roadmap, CI test count).

**Live URL (after Pages is enabled):** https://apxv-official.github.io/APXV/

**Preview locally:** `preview.ps1` or `preview.bat` → http://127.0.0.1:5500

Edit here, then push `main`. Workflow **Deploy static content to Pages** runs on every push to `main`.

## Republish after Pages was disabled

1. Repo **Settings → Pages**
2. Under **Build and deployment**, click **Static HTML** (GitHub Actions) — do **not** pick Jekyll
3. If GitHub offers to commit a workflow, **cancel** — this repo already has `.github/workflows/pages.yml`
4. **Actions** → **Deploy static content to Pages** → **Run workflow** → branch `main`
5. When the run is green, open https://apxv-official.github.io/APXV/ (hard refresh with Ctrl+F5)