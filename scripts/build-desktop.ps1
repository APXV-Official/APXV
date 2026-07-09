# Build APXV desktop installer (MSI + NSIS). No git operations.
$ErrorActionPreference = "Stop"

$DevRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$UiRoot = Join-Path $DevRoot "ui"

Write-Host "Staging runtime payload for MSI bundle..."
& (Join-Path $PSScriptRoot "stage-desktop-runtime.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Building APXV web assets..."
Push-Location $UiRoot
pnpm --filter @apxv/web build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Building APXV desktop (release)..."
if ($env:APXV_WINDOWS_BUNDLES) {
    Write-Host "  bundles: $($env:APXV_WINDOWS_BUNDLES)"
    pnpm --filter @apxv/desktop exec tauri build --bundles $env:APXV_WINDOWS_BUNDLES
} else {
    pnpm --filter @apxv/desktop build
}
if (-not $?) {
    Write-Error "Desktop tauri build failed"
    exit 1
}
Pop-Location

$releaseExe = Join-Path $UiRoot "apps\desktop\src-tauri\target\release\apxv.exe"
if (-not (Test-Path $releaseExe)) {
    Write-Error "Release binary missing: $releaseExe"
    exit 1
}

$TauriRoot = Join-Path $UiRoot "apps\desktop\src-tauri"
$msiDir = Join-Path $TauriRoot "target\release\bundle\msi"
$nsisDir = Join-Path $TauriRoot "target\release\bundle\nsis"

Write-Host ""
Write-Host "Build complete."
if (Test-Path $releaseExe) {
    Write-Host "  Binary: $releaseExe"
}
Get-ChildItem $msiDir -Filter "*.msi" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  MSI:    $($_.FullName)"
}
Get-ChildItem $nsisDir -Filter "*setup.exe" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Setup:  $($_.FullName)"
}

$msi = @(Get-ChildItem $msiDir -Filter "*.msi" -ErrorAction SilentlyContinue)
$setup = @(Get-ChildItem $nsisDir -Filter "*setup.exe" -ErrorAction SilentlyContinue)
if ($msi.Count -eq 0 -or $setup.Count -eq 0) {
    Write-Error "Installer bundles missing (msi=$($msi.Count), setup=$($setup.Count)). target/release tree:"
    $releaseRoot = Join-Path $TauriRoot "target\release"
    if (Test-Path $releaseRoot) {
        Get-ChildItem $releaseRoot -Recurse -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_.FullName }
    } else {
        Write-Host "  (missing $releaseRoot)"
    }
    exit 1
}