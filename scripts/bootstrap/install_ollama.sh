#!/usr/bin/env bash
# APXV — Install Ollama on Linux/macOS and pull llama3.2
set -euo pipefail

MODEL="${APXV_OLLAMA_MODEL:-llama3.2}"

if ! command -v ollama >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
  elif command -v brew >/dev/null 2>&1; then
    brew install ollama
  else
    echo "No supported package manager — install Ollama from https://ollama.com/download" >&2
    exit 1
  fi
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama not on PATH after install" >&2
  exit 1
fi

ollama pull "${MODEL}"
echo "Ollama ready: ${MODEL}"