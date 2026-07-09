# Build APXV desktop installer (MSI + NSIS). No git operations.
$ErrorActionPreference = "Stop"

$DevRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$UiRoot = Join-Path $DevRoot "ui"
$DesktopRoot = Join-Path $UiRoot "apps\desktop"
$TauriRoot = Join-Path $DesktopRoot "src-tauri"

Write-Host "Staging runtime payload for MSI bundle..."
& (Join-Path $PSScriptRoot "stage-desktop-runtime.ps1")
if (-not $?) { exit 1 }

Write-Host "Building APXV web assets..."
Push-Location $UiRoot
pnpm --filter @apxv/web build
if (-not $?) { exit 1 }

Write-Host "Building APXV desktop (release)..."
Push-Location $DesktopRoot
if ($env:APXV_WINDOWS_BUNDLES) {
    Write-Host "  bundles: $($env:APXV_WINDOWS_BUNDLES)"
    pnpm exec -- tauri build --verbose --bundles $env:APXV_WINDOWS_BUNDLES
} else {
    # Skip package.json prebuild (staging already ran); invoke tauri directly like Linux CI.
    pnpm exec -- tauri build --verbose
}
if (-not $?) { exit 1 }
Pop-Location
Pop-Location

$releaseExe = Join-Path $TauriRoot "target\release\apxv.exe"
$msiDir = Join-Path $TauriRoot "target\release\bundle\msi"
$nsisDir = Join-Path $TauriRoot "target\release\bundle\nsis"

if (-not (Test-Path $releaseExe)) {
    Write-Error "Release binary missing: $releaseExe"
    exit 1
}

$msi = @(Get-ChildItem $msiDir -Filter "*.msi" -ErrorAction SilentlyContinue)
$setup = @(Get-ChildItem $nsisDir -Filter "*setup.exe" -ErrorAction SilentlyContinue)
if ($msi.Count -eq 0 -or $setup.Count -eq 0) {
    Write-Error "Installer bundles missing (msi=$($msi.Count), setup=$($setup.Count))."
    $releaseRoot = Join-Path $TauriRoot "target\release"
    if (Test-Path $releaseRoot) {
        Get-ChildItem $releaseRoot -Recurse -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_.FullName }
    }
    exit 1
}

Write-Host ""
Write-Host "Build complete."
Write-Host "  Binary: $releaseExe"
$msi | ForEach-Object { Write-Host "  MSI:    $($_.FullName)" }
$setup | ForEach-Object { Write-Host "  Setup:  $($_.FullName)" }