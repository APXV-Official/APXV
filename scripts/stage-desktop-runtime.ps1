# Stage runtime payload for Tauri MSI bundle (no operator managed/ or keys/).
$ErrorActionPreference = "Stop"

$DevRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeRoot = Join-Path $DevRoot "runtime"
if (-not (Test-Path (Join-Path $RuntimeRoot "pyproject.toml"))) {
    $RuntimeRoot = $DevRoot
}
$PayloadRoot = Join-Path $DevRoot "ui\apps\desktop\runtime-payload"

$includeDirs = @(
    "agents",
    "governance-libraries",
    "scripts",
    "rust",
    "examples",
    "docs"
)
$includeFiles = @(
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "README.md"
)

if (Test-Path $PayloadRoot) {
    Remove-Item -Recurse -Force $PayloadRoot
}
New-Item -ItemType Directory -Path $PayloadRoot | Out-Null

foreach ($dir in $includeDirs) {
    $src = Join-Path $RuntimeRoot $dir
    if (-not (Test-Path $src)) { continue }
    $dst = Join-Path $PayloadRoot $dir
    if ($dir -eq "rust") {
        # Ship workspace sources + release prover binaries — no operator keys/.
        Copy-Item -Recurse -Force $src $dst
        Get-ChildItem -Path $dst -Recurse -Directory -Filter "keys" | ForEach-Object {
            Get-ChildItem $_.FullName -File | Remove-Item -Force
        }
        if (Test-Path (Join-Path $dst "target")) {
            Remove-Item -Recurse -Force (Join-Path $dst "target\debug") -ErrorAction SilentlyContinue
        }
        $releaseDir = Join-Path $dst "target\release"
        if (Test-Path $releaseDir) {
            # Ship Windows prover binaries only in MSI payload.
            @("apxv-zk", "apxv-circuits", "apx-zk", "apx-circuits") | ForEach-Object {
                $unixBin = Join-Path $releaseDir $_
                if (Test-Path $unixBin) { Remove-Item -Force $unixBin -ErrorAction SilentlyContinue }
            }
        }
        continue
    }
    Copy-Item -Recurse -Force $src $dst
    if ($dir -eq "docs") {
        Remove-Item -Recurse -Force (Join-Path $dst "internal"), (Join-Path $dst "resume") -ErrorAction SilentlyContinue
    }
}

$govSpecs = @(
    "rules\rule1.md",
    "workflows\workflow1.md",
    "knowledge\knowledge1.md"
)
foreach ($spec in $govSpecs) {
    $srcSpec = Join-Path $RuntimeRoot "managed\$spec"
    $dstSpec = Join-Path $PayloadRoot "managed\$spec"
    if (Test-Path $srcSpec) {
        $dstDir = Split-Path $dstSpec -Parent
        if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
        Copy-Item -Force $srcSpec $dstSpec
    }
}

foreach ($file in $includeFiles) {
    $src = Join-Path $RuntimeRoot $file
    if (Test-Path $src) {
        Copy-Item -Force $src (Join-Path $PayloadRoot $file)
    }
}

Write-Host "Staged desktop runtime payload -> $PayloadRoot"