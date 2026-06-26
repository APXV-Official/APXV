# APXV1 — Docker-only onboarding (no local Python or Rust required).
param(
    [switch]$Fresh
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "============================================================"
Write-Host "APXV1 Docker onboarding (v1.1.1)"
Write-Host "Requires: Docker Desktop + Docker Compose"
Write-Host "============================================================"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
}

$useComposePlugin = $false
docker compose version 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $useComposePlugin = $true
} elseif (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Error "Docker Compose not found."
}

function Invoke-Compose {
    param([string[]]$Args)
    if ($useComposePlugin) {
        & docker compose @Args
    } else {
        & docker-compose @Args
    }
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed: $Args" }
}

if ($Fresh -and (Test-Path "managed")) {
    $bak = "managed.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
    Write-Host "Moving existing managed/ to $bak"
    Move-Item -LiteralPath "managed" -Destination $bak
}

Write-Host "[1/3] Building image (Rust + Python + ZK keys — may take several minutes)..."
Invoke-Compose @("build")

Write-Host "[2/3] Onboarding in container (pack demo, attest, verify)..."
Invoke-Compose @("run", "--rm", "apx-v1", "python", "-m", "scripts.onboard", "--skip-zk")

Write-Host "[3/3] Starting API server..."
Invoke-Compose @("up", "-d")

Write-Host "============================================================"
Write-Host "Docker onboarding complete."
Write-Host "  Health:  curl http://127.0.0.1:8741/health"
Write-Host "  Logs:    docker logs apx-v1"
Write-Host "  Stop:    docker compose down"
Write-Host "============================================================"