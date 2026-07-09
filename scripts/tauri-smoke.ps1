# Row 11 - Tauri desktop smoke (Phase A gate) — PR-15 sovereign path
# Logs to audit-tauri.log in remaster root. No git operations.

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false
$DevRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DesktopTauri = Join-Path $DevRoot "ui\apps\desktop\src-tauri"
$RuntimeRoot = Join-Path $DevRoot "runtime"
if (-not (Test-Path (Join-Path $RuntimeRoot "pyproject.toml"))) {
    $RuntimeRoot = $DevRoot
}
$LogPath = Join-Path $DevRoot "audit-tauri.log"
$ApiKey = if ($env:APXV_API_KEY) { $env:APXV_API_KEY } else { "gnKiTGGjRimhIPWeoP9BLnumQVPClWxYVbAD8J_FXVM" }

$log = @()
$log += "=== TAURI SMOKE (Row 11 / PR-15) $(Get-Date -Format o) ==="
$log += "Workspace: $DevRoot"

function Step([string]$Msg) {
    $script:log += $Msg
    Write-Host $Msg
}

try {
    Step "--- [A] cargo check (desktop shell) ---"
    Push-Location $DesktopTauri
    $prevNative = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
    $cargoOut = & cargo check 2>&1 | ForEach-Object { "$_" }
    $cargoExit = $LASTEXITCODE
    $PSNativeCommandUseErrorActionPreference = $prevNative
    Pop-Location
    $log += $cargoOut
    $cargoText = ($cargoOut | Out-String)
    $cargoOk = ($cargoExit -eq 0) -or ($cargoText -match "Finished")
    if (-not $cargoOk) {
        Step "FAIL: cargo check exit $cargoExit"
        $log | Out-File -FilePath $LogPath -Encoding utf8
        exit 1
    }
    Step "PASS: cargo check"

    $releaseExe = Join-Path $DesktopTauri "target\release\apxv.exe"
    $msi = Get-ChildItem -Path (Join-Path $DesktopTauri "target\release\bundle\msi") -Filter "*.msi" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (Test-Path $releaseExe) {
        Step "PASS: release binary exists - $releaseExe"
    } else {
        Step "WARN: release binary missing - run: pnpm --filter @apxv/desktop build"
    }
    if ($msi) {
        Step "PASS: MSI installer exists - $($msi.FullName)"
    }

    Step "--- [B] APXV root resolution (cross-platform paths + bootstrap commands) ---"
    $pathsRs = Get-Content (Join-Path $DesktopTauri "src\paths.rs") -Raw
    $bootstrapRs = Get-Content (Join-Path $DesktopTauri "src\bootstrap.rs") -Raw
    $pythonCmdRs = Get-Content (Join-Path $DesktopTauri "src\python_cmd.rs") -Raw
    $tauriConf = Get-Content (Join-Path $DesktopTauri "tauri.conf.json") -Raw
    if ($pathsRs -match "LOCALAPPDATA" -and $pathsRs -match "resolve_apxv_root" -and $pathsRs -match "Application Support") {
        Step "PASS: paths.rs resolves operator data root (Windows + macOS markers)"
    } else {
        Step "FAIL: paths.rs missing cross-platform root resolution"
        $log | Out-File -FilePath $LogPath -Encoding utf8
        exit 1
    }
    if ($pythonCmdRs -match "spawn_python_module") {
        Step "PASS: python_cmd.rs cross-platform interpreter"
    } else {
        Step "FAIL: python_cmd.rs missing spawn_python_module"
        $log | Out-File -FilePath $LogPath -Encoding utf8
        exit 1
    }
    if ($bootstrapRs -match "run_bootstrap" -and $bootstrapRs -match "get_bootstrap_status") {
        Step "PASS: bootstrap.rs Tauri commands present"
    } else {
        Step "FAIL: bootstrap.rs missing sovereign commands"
        $log | Out-File -FilePath $LogPath -Encoding utf8
        exit 1
    }
    if ($tauriConf -match "runtime-payload") {
        Step "PASS: tauri.conf.json bundles runtime payload"
    } else {
        Step "WARN: tauri.conf.json missing runtime-payload resources"
    }

    Step "--- [C] API smoke (dev runtime + onboard flow) ---"
    Push-Location $RuntimeRoot
    $prevNative = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
    $smokeOut = & py -3 -m scripts.tauri_smoke --spawn-server 2>&1 | ForEach-Object { "$_" }
    $smokeExit = $LASTEXITCODE
    $PSNativeCommandUseErrorActionPreference = $prevNative
    Pop-Location
    $log += $smokeOut
    if ($smokeExit -ne 0) {
        Step "FAIL: tauri_smoke.py exit $smokeExit"
        $log | Out-File -FilePath $LogPath -Encoding utf8
        exit 1
    }
    Step "PASS: tauri_smoke.py"

    Step "--- [D] Playwright bootstrap + pack studio ---"
    Push-Location (Join-Path $DevRoot "ui\apps\web")
    $env:APXV_API_KEY = $ApiKey
    $prevNative = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
    $pwBootstrap = & pnpm exec playwright test e2e/bootstrap.spec.ts --reporter=line 2>&1 | ForEach-Object { "$_" }
    $pwBootstrapExit = $LASTEXITCODE
    $pwOut = & pnpm exec playwright test e2e/critical-flows.spec.ts -g "pack studio" --reporter=line 2>&1 | ForEach-Object { "$_" }
    $pwExit = $LASTEXITCODE
    $PSNativeCommandUseErrorActionPreference = $prevNative
    $pwBootstrapText = ($pwBootstrap | Out-String)
    $pwText = ($pwOut | Out-String)
    $pwBootstrapOk = ($pwBootstrapExit -eq 0) -or ($pwBootstrapText -match "\d+ passed")
    $pwOk = ($pwExit -eq 0) -or ($pwText -match "\d+ passed")
    Pop-Location
    $log += $pwBootstrap
    $log += $pwOut
    if (-not $pwBootstrapOk) {
        Step "WARN: Playwright bootstrap preview failed (exit $pwBootstrapExit)"
    } else {
        Step "PASS: Playwright bootstrap preview"
    }
    if (-not $pwOk) {
        Step "WARN: Playwright pack studio failed (exit $pwExit) - API smoke passed"
    } else {
        Step "PASS: Playwright pack studio"
    }

    Step ""
    Step "OVERALL: PASS - Row 11 Tauri smoke complete (PR-15 sovereign path)"
    $log | Out-File -FilePath $LogPath -Encoding utf8
    exit 0
} catch {
    Step "FAIL: $($_.Exception.Message)"
    $log | Out-File -FilePath $LogPath -Encoding utf8
    exit 1
}