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
pnpm --filter @apxv/desktop build
$buildExit = $LASTEXITCODE
Pop-Location

if ($buildExit -ne 0) { exit $buildExit }

$TauriRoot = Join-Path $UiRoot "apps\desktop\src-tauri"
$releaseExe = Join-Path $TauriRoot "target\release\apxv.exe"
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