# APXV1 — one-command onboarding (Windows). Requires Python 3.9+ and Rust.
param(
    [switch]$Fresh
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "============================================================"
Write-Host "APXV1 — clone to running (v1.1.1)"
Write-Host "No Python/Rust? Use: .\scripts\install-docker.ps1"
Write-Host "============================================================"

$Python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = @("python")
} else {
    Write-Error "Python not found. Install Python 3.9+ or run .\scripts\install-docker.ps1 (Docker only)."
}

$pyVersion = & $Python[0] $Python[1..($Python.Length - 1)] -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python: $pyVersion"

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Rust not found. Install Rust (docs/INSTALL-RUST.md) or run .\scripts\install-docker.ps1 (Docker only)."
}

if ($Fresh) {
    Write-Host "Resetting runtime state (keeping governance templates)..."
    & $Python[0] $Python[1..($Python.Length - 1)] -m scripts.fresh_reset
    if ($LASTEXITCODE -ne 0) { throw "fresh_reset failed (exit $LASTEXITCODE)" }
}

Write-Host "[1/2] Installing Python package (dev + voice extras)..."
& $Python[0] $Python[1..($Python.Length - 1)] -m pip install -e ".[dev,voice]"
if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)" }

Write-Host "[2/2] Onboarding (setup, pack demo, attest, verify)..."
& $Python[0] $Python[1..($Python.Length - 1)] -m scripts.onboard
if ($LASTEXITCODE -ne 0) { throw "onboard failed (exit $LASTEXITCODE)" }

Write-Host "============================================================"
Write-Host "Done. Optional: python -m scripts.setup_voice"
Write-Host "Docs: docs/QUICKSTART.md"
Write-Host "============================================================"