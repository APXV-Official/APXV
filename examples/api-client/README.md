# API Client Example

Python client for the local APXV1 HTTP API.

## Prerequisites

1. Run setup: `python -m scripts.setup_first_run`
2. Start the server: `python -m scripts.apx_serve`
3. Set your API key:

```bash
# PowerShell
$env:APX_API_KEY = "your-key-here"

# Bash
export APX_API_KEY="your-key-here"
```

### Where to find the key

| Source | When |
|--------|------|
| Onboard / `setup_first_run` output | Printed once when the default key is created |
| `managed/config/OPERATOR-KEY-default-operator.txt` | Written automatically (v1.2.1+) |
| `apx_ctl api-key create` | Any time; use `--save-hint` to write a hint file |

```bash
python -m scripts.apx_ctl api-key create my-app --save-hint
```

New keys work immediately while `apx_serve` is running (v1.2.1+). Hashes are stored in `managed/config/api_keys.json` — raw keys cannot be recovered from that file.

## Run

```bash
python examples/api-client/run_pipeline.py
```

On Linux/WSL use `python3` if `python` is not on PATH.

## What It Does

1. Checks `/health`
2. Queues an async pipeline job via `POST /pipeline/run`
3. Polls `/jobs/{id}` until complete

See [docs/LOCAL-API.md](../../docs/LOCAL-API.md) for all endpoints.