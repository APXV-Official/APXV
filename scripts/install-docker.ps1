# APXV - Docker-only onboarding (no local Python or Rust required).
param(
    [switch]$Fresh
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "============================================================"
Write-Host "APXV Docker onboarding (v1.3.0)"
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
    param([string[]]$ComposeArgs)
    # Docker Compose v2 writes progress to stderr; suppress native stderr-as-error (F-018 parity).
    $prevEap = $ErrorActionPreference
    $prevNative = $PSNativeCommandUseErrorActionPreference
    $ErrorActionPreference = "Continue"
    $PSNativeCommandUseErrorActionPreference = $false
    try {
        if ($useComposePlugin) {
            & docker compose @ComposeArgs 2>&1 | Out-Host
        } else {
            & docker-compose @ComposeArgs 2>&1 | Out-Host
        }
        if ($LASTEXITCODE -ne 0) { throw "docker compose failed: $ComposeArgs" }
    } finally {
        $ErrorActionPreference = $prevEap
        $PSNativeCommandUseErrorActionPreference = $prevNative
    }
}

function Reset-ApxFreshRuntime {
    $dirs = @(
        "managed\artifacts", "managed\audit", "managed\backups", "managed\config", "managed\store",
        "rust\apxv-circuits\keys", "rust\apxv-zk\keys"
    )
    foreach ($d in $dirs) {
        if (Test-Path $d) {
            Write-Host "Removing $d"
            Remove-Item -LiteralPath $d -Recurse -Force
        }
    }
}

function Ensure-GovernanceTemplates {
    $required = @("managed\rules", "managed\workflows", "managed\knowledge")
    $missing = $required | Where-Object { -not (Test-Path $_) }
    if ($missing.Count -eq 0) { return }

    Write-Host "Restoring governance templates..."
    if (Get-Command git -ErrorAction SilentlyContinue) {
        & git checkout -- managed/rules managed/workflows managed/knowledge managed/config/.gitkeep 2>$null
        $missing = $required | Where-Object { -not (Test-Path $_) }
        if ($missing.Count -eq 0) { return }
    }

    $pack = "governance-libraries\apxv-pack-reference-redaction\governance"
    New-Item -ItemType Directory -Force -Path "managed\rules", "managed\workflows", "managed\knowledge" | Out-Null
    Copy-Item "$pack\rules\RULE-RED-001.md" "managed\rules\rule1.md" -Force
    Copy-Item "$pack\workflows\WORKFLOW-RED-001.md" "managed\workflows\workflow1.md" -Force
    Copy-Item "$pack\knowledge\KB-RED-001.md" "managed\knowledge\knowledge1.md" -Force
}

if ($Fresh) {
    Write-Host "Resetting runtime state (keeping governance templates)..."
    Reset-ApxFreshRuntime
}
Ensure-GovernanceTemplates

if (Get-NetTCPConnection -LocalPort 8741 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Port 8741 in use - stopping any existing apxv container..."
    try { Invoke-Compose @("down") } catch {}
}

Write-Host "[1/4] Building image (Rust + Python — no vendor keys in image)..."
Invoke-Compose @("build")

Write-Host "[2/4] Sovereign bootstrap (generates ZK keys on host volumes)..."
Write-Host "      First run may take several minutes (11-circuit trusted setup)."
Invoke-Compose @(
    "run", "--rm", "apxv", "python", "-m", "scripts.apxv_bootstrap",
    "--skip-ollama", "--skip-voice", "--skip-smoke", "--skip-prover-build"
)

Write-Host "[3/4] Pack demo + attest + verify..."
Invoke-Compose @("run", "--rm", "apxv", "python", "-m", "scripts.onboard", "--skip-setup")

Write-Host "[4/4] Starting API server..."
# Remove stale containers from prior installs (v1.2 apx-v1 + v1.3 apxv)
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker rm -f apx-v1 2>&1 | Out-Null
docker rm -f apxv 2>&1 | Out-Null
$ErrorActionPreference = $prevEap
Invoke-Compose @("up", "-d")

Write-Host "============================================================"
Write-Host "Docker onboarding complete."
Write-Host "  Health:  curl http://127.0.0.1:8741/health"
Write-Host "  Logs:    docker logs apxv"
Write-Host "  Stop:    docker compose down"
Write-Host "============================================================"