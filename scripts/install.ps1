# APXV — DEPRECATED: use install-full.ps1 (v1.3 sovereign) or install-docker.ps1 (teams).
param(
    [switch]$Fresh
)

$ErrorActionPreference = "Stop"
Write-Host "============================================================"
Write-Host "NOTE: install.ps1 is deprecated in v1.3."
Write-Host "  Native sovereign:  .\scripts\install-full.ps1"
Write-Host "  Docker (teams):    .\scripts\install-docker.ps1"
Write-Host "============================================================"

$target = Join-Path $PSScriptRoot "install-full.ps1"
if (-not (Test-Path $target)) {
    throw "Missing install-full.ps1 — restore from apxv-v1.3-remaster runtime/scripts"
}

if ($Fresh) {
    & $target -Fresh
} else {
    & $target
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }