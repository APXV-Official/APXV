# Verify built desktop binary: auto-start on launch + relaunch (minimal PATH like Explorer).
# Run AFTER build-desktop.ps1 produces target\release\apxv.exe
$ErrorActionPreference = "Stop"
$DevRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ReleaseExe = Join-Path $DevRoot "ui\apps\desktop\src-tauri\target\release\apxv.exe"
$Port = 8741
$Pass = 0
$Fail = 0

function Ok($m) { Write-Host "[PASS] $m"; $script:Pass++ }
function Bad($m) { Write-Host "[FAIL] $m"; $script:Fail++ }

function Test-PortOpen {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $Port)
        $c.Close()
        return $true
    } catch { return $false }
}

function Stop-AllApxv {
    Get-Process -Name apxv -ErrorAction SilentlyContinue | ForEach-Object {
        taskkill /F /T /PID $_.Id 2>$null | Out-Null
    }
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { taskkill /F /T /PID $_.OwningProcess 2>$null | Out-Null }
    Start-Sleep -Seconds 1
}

Write-Host "=== Desktop lifecycle verify (built apxv.exe) ==="
if (-not (Test-Path $ReleaseExe)) {
    Write-Error "Build apxv.exe first: .\scripts\build-desktop.ps1"
    exit 1
}
Write-Host "Binary: $ReleaseExe"

Stop-AllApxv
if (Test-PortOpen) { Bad "port :$Port busy before test" } else { Ok "port :$Port free before test" }

function Start-ApxvMinimalPath {
    param([string]$Exe)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.UseShellExecute = $false
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
    $psi.Environment["PATH"] = "C:\Windows\system32;C:\Windows"
    $psi.Environment["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:8741"
    return [System.Diagnostics.Process]::Start($psi)
}

$proc = Start-ApxvMinimalPath -Exe $ReleaseExe

$opened = $false
for ($i = 0; $i -lt 90; $i++) {
    if (Test-PortOpen) { $opened = $true; break }
    if ($proc.HasExited) { break }
    Start-Sleep -Seconds 1
}
if ($opened) {
    Ok "auto-start opened :$Port within 90s (pid $($proc.Id))"
} else {
    Bad "auto-start failed - port :$Port closed (exe exited=$($proc.HasExited))"
}

if (-not $proc.HasExited) {
    Stop-AllApxv
    Start-Sleep -Seconds 1
    if (-not (Test-PortOpen)) { Ok "port :$Port released after desktop stop" } else { Bad "port :$Port stuck after stop" }
}

$proc2 = Start-ApxvMinimalPath -Exe $ReleaseExe
$reopened = $false
for ($i = 0; $i -lt 90; $i++) {
    if (Test-PortOpen) { $reopened = $true; break }
    Start-Sleep -Seconds 1
}
if ($reopened) {
    Ok "relaunch auto-start opened :$Port (pid $($proc2.Id))"
} else {
    Bad "relaunch failed to open :$Port"
}

Stop-AllApxv
Write-Host ""
Write-Host "=== Summary: $Pass passed, $Fail failed ==="
if ($Fail -gt 0) { exit 1 }