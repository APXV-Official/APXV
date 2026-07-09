# APXV — pack demo, attest, verify (instance must already be set up).
param(
    [ValidateSet("reference", "document", "ai", "all")]
    [string]$Pack = "reference"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = $null
if (Test-Path "$Root\.venv\Scripts\python.exe") {
    $Python = @("$Root\.venv\Scripts\python.exe")
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = @("python")
} else {
    Write-Error "Python not found. Run .\scripts\install.ps1 first."
}

& $Python[0] $Python[1..($Python.Length - 1)] -m scripts.apxv_demo --pack $Pack
if ($LASTEXITCODE -ne 0) { throw "apxv_demo failed (exit $LASTEXITCODE)" }