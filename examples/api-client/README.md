# API Client Example

Python client for the local APXV1 HTTP API.

## Prerequisites

1. Run setup: `python -m scripts.setup_first_run`
2. Start the server: `python -m scripts.apx_serve`
3. Set your API key (printed once during setup):

```bash
# PowerShell
$env:APX_API_KEY = "your-key-here"

# Bash
export APX_API_KEY="your-key-here"
```

## Run

```bash
python examples/api-client/run_pipeline.py
```

## What It Does

1. Checks `/health`
2. Queues an async pipeline job via `POST /pipeline/run`
3. Polls `/jobs/{id}` until complete

See [docs/LOCAL-API.md](../../docs/LOCAL-API.md) for all endpoints.