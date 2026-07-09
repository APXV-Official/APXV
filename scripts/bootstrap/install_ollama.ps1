# APXV — Install Ollama on Windows (winget) and pull llama3.2
$ErrorActionPreference = "Stop"

$model = if ($env:APXV_OLLAMA_MODEL) { $env:APXV_OLLAMA_MODEL } else { "llama3.2" }

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Error "winget not found — install Ollama manually from https://ollama.com/download"
    }
    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Error "ollama not on PATH after install — restart shell or sign in again"
}

ollama pull $model
if ($LASTEXITCODE -ne 0) {
    Write-Error "ollama pull $model failed with exit $LASTEXITCODE"
}

Write-Host "Ollama ready: $model"