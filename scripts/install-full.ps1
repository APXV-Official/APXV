# APXV — Native sovereign install (Rust + bootstrap + onboard). v1.3 power-user path.
param(
    [switch]$Fresh,
    [switch]$SkipOllama,
    [switch]$SkipVoice
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "============================================================"
Write-Host "APXV native install-full (v1.3.0 sovereign)"
Write-Host "Teams / no local Rust? Use: .\scripts\install-docker.ps1"
Write-Host "============================================================"

$Python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = @("python")
} else {
    Write-Error "Python not found. Install Python 3.9+ or run .\scripts\install-docker.ps1"
}

$pyVersion = & $Python[0] $Python[1..($Python.Length - 1)] -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python: $pyVersion"

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Rust not found. Install Rust (docs/INSTALL-RUST.md) or run .\scripts\install-docker.ps1"
}
if (-not (Get-Command rustc -ErrorAction SilentlyContinue)) {
    Write-Error "rustc not found. Install Rust (docs/INSTALL-RUST.md)"
}

if ($Fresh) {
    Write-Host "Resetting runtime state (keeping governance templates)..."
    & $Python[0] $Python[1..($Python.Length - 1)] -m scripts.fresh_reset
    if ($LASTEXITCODE -ne 0) { throw "fresh_reset failed (exit $LASTEXITCODE)" }
}

Write-Host "[1/5] Installing Python package (dev + voice extras)..."
& $Python[0] $Python[1..($Python.Length - 1)] -m pip install -e ".[dev,voice]"
if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)" }

Write-Host "[2/5] Building Rust provers (cargo build --release)..."
Push-Location rust
try {
    cargo build --release -p apxv-circuits -p apxv-zk
    if ($LASTEXITCODE -ne 0) { throw "cargo build failed (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}

$bootstrapArgs = @(
    $Python[0]
    $Python[1..($Python.Length - 1)]
    "-m", "scripts.apxv_bootstrap",
    "--profile", "production",
    "--skip-smoke"
)
if ($SkipOllama) { $bootstrapArgs += "--skip-ollama" }
if ($SkipVoice) { $bootstrapArgs += "--skip-voice" }

Write-Host "[3/5] Sovereign bootstrap (ZK keys + optional Ollama/Vosk)..."
Write-Host "      First run may take several minutes (11-circuit trusted setup)."
& @bootstrapArgs
$bootstrapExit = $LASTEXITCODE
if ($bootstrapExit -eq 2) {
    Write-Host "  Note: sovereign setup OK; optional integrations incomplete (exit 2)."
} elseif ($bootstrapExit -ne 0) {
    throw "apxv_bootstrap failed (exit $bootstrapExit)"
}

Write-Host "[4/5] Onboarding (pack demo + attest + verify)..."
& $Python[0] $Python[1..($Python.Length - 1)] -m scripts.onboard --skip-setup
if ($LASTEXITCODE -ne 0) { throw "onboard failed (exit $LASTEXITCODE)" }

Write-Host "[5/5] Complete."
Write-Host "============================================================"
Write-Host "Native sovereign install complete."
Write-Host "  Doctor:    py -3 -m scripts.apxv_doctor"
Write-Host "  Serve API: py -3 -m scripts.apxv_serve"
Write-Host "  Demo:      .\scripts\apxv_demo.ps1"
Write-Host "  install.json: managed\config\install.json"
Write-Host "============================================================"