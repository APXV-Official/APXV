# PR-2 validation (Windows): stop/start leaves a single listener on :8741.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Port = 8741
$Pass = 0
$Fail = 0

function Ok($msg) { Write-Host "[PASS] $msg"; $script:Pass++ }
function Bad($msg) { Write-Host "[FAIL] $msg"; $script:Fail++ }

function Test-PortOpen {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $Port)
        $c.Close()
        return $true
    } catch { return $false }
}

function Stop-PortListeners {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            $procId = $_.OwningProcess
            & taskkill.exe /F /T /PID $procId 2>$null | Out-Null
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    Start-Sleep -Milliseconds 500
}

Write-Host "=== PR-2 server lifecycle verify (Windows) ==="
Write-Host "ROOT=$Root"
Write-Host

Push-Location $Root
try {
    Stop-PortListeners
    Start-Sleep -Milliseconds 500
    if (Test-PortOpen) { Bad "port :$Port still open before test" } else { Ok "port :$Port free before start" }

    $serve = Start-Process -FilePath "py" -ArgumentList @("-3", "-m", "scripts.apxv_serve", "--bind", "127.0.0.1") -WorkingDirectory $Root -PassThru -WindowStyle Hidden
    for ($i = 0; $i -lt 40; $i++) {
        if (Test-PortOpen) { break }
        Start-Sleep -Milliseconds 250
    }
    if (Test-PortOpen) { Ok "apxv_serve opened :$Port (pid $($serve.Id))" } else { Bad "apxv_serve failed to open :$Port" }

    Stop-Process -Id $serve.Id -Force -ErrorAction SilentlyContinue
    Stop-PortListeners
    for ($i = 0; $i -lt 30; $i++) {
        if (-not (Test-PortOpen)) { break }
        Start-Sleep -Milliseconds 200
    }
    if (Test-PortOpen) { Bad "port :$Port still open after stop" } else { Ok "port :$Port released after stop" }

    $serve2 = Start-Process -FilePath "py" -ArgumentList @("-3", "-m", "scripts.apxv_serve", "--bind", "127.0.0.1") -WorkingDirectory $Root -PassThru -WindowStyle Hidden
    for ($i = 0; $i -lt 40; $i++) {
        if (Test-PortOpen) { break }
        Start-Sleep -Milliseconds 250
    }
    if (Test-PortOpen) { Ok "restart cycle - apxv_serve listening again (pid $($serve2.Id))" } else { Bad "restart cycle - port :$Port did not reopen" }
    Stop-Process -Id $serve2.Id -Force -ErrorAction SilentlyContinue
    Stop-PortListeners
} finally {
    Pop-Location
}

Write-Host
Write-Host "=== Summary: $Pass passed, $Fail failed (lifecycle gate) ==="
if ($Fail -gt 0) { exit 1 }