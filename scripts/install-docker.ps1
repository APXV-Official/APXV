# APXV1 - Docker-only onboarding (no local Python or Rust required).
param(
    [switch]$Fresh
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "============================================================"
Write-Host "APXV1 Docker onboarding (v1.2.5)"
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
    if ($useComposePlugin) {
        & docker compose @ComposeArgs
    } else {
        & docker-compose @ComposeArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed: $ComposeArgs" }
}

function Reset-ApxFreshRuntime {
    $dirs = @(
        "managed\artifacts", "managed\audit", "managed\backups", "managed\config", "managed\store",
        "rust\apx-circuits\keys", "rust\apx-zk\keys"
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
    Write-Host "Port 8741 in use - stopping any existing apx-v1 container..."
    try { Invoke-Compose @("down") } catch {}
}

function Seed-ZkKeysFromImage {
    $circuitsKeys = "rust\apx-circuits\keys"
    $zkKeys = "rust\apx-zk\keys"
    $circuitsEmpty = -not (Test-Path $circuitsKeys) -or -not (Get-ChildItem $circuitsKeys -ErrorAction SilentlyContinue)
    $zkEmpty = -not (Test-Path $zkKeys) -or -not (Get-ChildItem $zkKeys -ErrorAction SilentlyContinue)
    if (-not $circuitsEmpty -and -not $zkEmpty) { return }

    Write-Host "Seeding ZK keys from image (volume mounts hide baked-in keys)..."
    New-Item -ItemType Directory -Force -Path "rust\apx-circuits", "rust\apx-zk" | Out-Null
    $cid = docker create apx-v1:latest
    try {
        docker cp "${cid}:/app/rust/apx-circuits/keys" "rust/apx-circuits/"
        docker cp "${cid}:/app/rust/apx-zk/keys" "rust/apx-zk/"
        if ($LASTEXITCODE -ne 0) { throw "docker cp failed seeding ZK keys" }
    } finally {
        docker rm $cid | Out-Null
    }
}

Write-Host "[1/3] Building image (Rust + Python + ZK keys - may take several minutes)..."
Invoke-Compose @("build")
Seed-ZkKeysFromImage

Write-Host "[2/3] Onboarding in container (pack demo, attest, verify)..."
Invoke-Compose @("run", "--rm", "apx-v1", "python", "-m", "scripts.onboard", "--skip-zk")

Write-Host "[3/3] Starting API server..."
# Remove stale apx-v1 from a prior install (port 8741 / container name conflict)
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker rm -f apx-v1 2>&1 | Out-Null
$ErrorActionPreference = $prevEap
Invoke-Compose @("up", "-d")

Write-Host "============================================================"
Write-Host "Docker onboarding complete."
Write-Host "  Health:  curl http://127.0.0.1:8741/health"
Write-Host "  Logs:    docker logs apx-v1"
Write-Host "  Stop:    docker compose down"
Write-Host "============================================================"