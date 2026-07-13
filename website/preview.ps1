$Port = 5500
$Root = $PSScriptRoot
$Url = "http://127.0.0.1:$Port/"

Write-Host ""
Write-Host "APXV site preview" -ForegroundColor Cyan
Write-Host "URL: $Url"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

Set-Location $Root
Start-Process $Url
py -3 -m http.server $Port --bind 127.0.0.1