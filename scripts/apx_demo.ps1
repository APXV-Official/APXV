# Deprecated wrapper — use scripts/apxv_demo.ps1 (removed in v1.4).
param(
    [ValidateSet("reference", "document", "ai", "all")]
    [string]$Pack = "reference"
)
Write-Warning "apx_demo.ps1 is deprecated; use apxv_demo.ps1"
& (Join-Path $PSScriptRoot "apxv_demo.ps1") -Pack $Pack