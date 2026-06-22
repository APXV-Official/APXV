# APXV1 — Cross-platform install + verify (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "============================================================"
Write-Host "APXV1 Install"
Write-Host "============================================================"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Install Python 3.9+ from https://www.python.org/downloads/"
}

$pyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python: $pyVersion"

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Warning "Rust toolchain not found. ZK setup will fail. See docs/INSTALL-RUST.md"
}

Write-Host "[1/5] Installing Python package..."
python -m pip install -e ".[dev,voice]"

Write-Host "[2/5] First-run setup (includes ZK keys)..."
python -m scripts.setup_first_run

Write-Host "[3/5] Doctor check..."
python -m scripts.apx_doctor

Write-Host "[4/5] Pipeline + attestation..."
python -m scripts.run_apx --attest

Write-Host "[5/5] Independent proof verification..."
python -m scripts.verify_attestation --real-zk

Write-Host "============================================================"
Write-Host "APXV1 install complete."
Write-Host "Optional voice model: python -m scripts.setup_voice"
Write-Host "Ceremony (releases): python -m scripts.ceremony_transcript --write --tier B"
Write-Host "Next: python -m scripts.apx_serve"
Write-Host "Docs: docs/QUICKSTART.md"
Write-Host "============================================================"