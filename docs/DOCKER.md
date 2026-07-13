# Docker Deployment

Run APXV as a local API service for team/company use.

## Quick start (no local Python or Rust)

```bash
./scripts/install-docker.sh
curl http://127.0.0.1:8741/health
```

This builds the image, runs full onboarding in a one-off container (pack demo + attest + verify), then starts the API.

Manual equivalent:

```bash
docker compose up -d --build
curl http://127.0.0.1:8741/health
```

APXV binds inside the container on `0.0.0.0:8741` (Docker-only via `APXV_CONTAINER_BIND=1`). Host access is still localhost-only via compose port mapping.

## First-time setup in container

On first start with **empty volumes**, the entrypoint runs `apxv_bootstrap` (sovereign ZK keys generated on mounted volumes — no vendor keys in the image).

Get your API key (v1.2.1+):

1. Read the hint file on the mounted volume: `managed/config/OPERATOR-KEY-default-operator.txt`
2. Or scan container logs: `docker logs apxv 2>&1 | findstr /i "API KEY"`

Save the key and delete the hint file after copying if desired. See [LOCAL-API.md](LOCAL-API.md) for auth details.

Create additional keys after start (accepted immediately without restarting the API):

```bash
docker exec apxv python -m scripts.apxv_ctl api-key create team-api --save-hint
```

The hint is written to `managed/config/OPERATOR-KEY-team-api.txt` on the mounted volume.

## Volumes (important)

`docker-compose.yml` mounts:

| Host path | Purpose |
|-----------|---------|
| `./managed` | Artifacts, config, audit, store |
| `./rust/apxv-circuits/keys` | Governance ZK keys |
| `./rust/apxv-zk/keys` | Entity ZK keys |

### Use fresh volumes for production-like deploys

Do **not** mount a developer `managed/` directory with a long audit history. That can show `degraded` health from prior local experiments (v1.2.2+ reports `integrity.audit_summary` with `chain_break` vs `corrupt_lines`). See [RUNBOOKS/RUNBOOK-UPGRADE.md](../RUNBOOKS/RUNBOOK-UPGRADE.md).

For a clean deploy:

```bash
mkdir -p managed-empty rust-keys-empty
# point compose volumes to empty dirs, or remove ./managed and let Docker create it
docker compose up -d --build
```

## Health check

```bash
curl http://127.0.0.1:8741/health
```

Expect `"status": "healthy"` on a fresh instance.

## Backup

```bash
docker exec apxv python -m scripts.apxv_ctl backup-create
```

Backups land in `managed/backups/` on the mounted volume.

## Run pipeline inside container

```bash
docker exec apxv python -m scripts.run_apxv --attest
docker exec apxv python -m scripts.verify_attestation --real-zk
```

## Troubleshooting

**`container name "/apxv" is already in use`** (or legacy **`/apx-v1`** from v1.2 installs)

Only one APXV API per host on port 8741. Remove stale containers, then start again:

```bash
docker rm -f apxv apx-v1
docker compose up -d
```

`install-docker.sh` and `install-docker.ps1` run this cleanup automatically (v1.2.2+; bash since v1.2.1). On Windows PowerShell, the PS1 script ignores benign `No such container` stderr from `docker rm` so a second install in the same clone completes without manual steps.

## Operator UI (Docker + nginx)

Serve the built APXV UI on **http://127.0.0.1:5173** alongside the API:

```bash
# From runtime/ — API already running or start both:
docker compose -f docker-compose.yml -f docker-compose.ui.yml up -d --build
```

| Service | URL | Notes |
|---------|-----|--------|
| `apxv` | http://127.0.0.1:8741 | API (CORS allows UI origin `:5173`) |
| `apxv-ui` | http://127.0.0.1:5173 | nginx static build of `@apxv/web` |

Onboarding: paste operator key from `managed/config/OPERATOR-KEY-*.txt` (same as native or desktop).

Sovereign trust: [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md) · Desktop alternative: [INSTALL-USER.md](INSTALL-USER.md)

Smoke gate: `..\scripts\docker-ui-smoke.ps1` (logs `audit-docker-ui.log`).

Stop both:

```bash
docker compose -f docker-compose.yml -f docker-compose.ui.yml down
```

## Ollama and voice (host integrations)

The API container does **not** bundle Ollama or Vosk models. For AI Governance and voice workflows:

| Approach | When to use |
|----------|-------------|
| **Host Ollama** | Install Ollama on the Docker host (`scripts/bootstrap/install_ollama.sh` or `.ps1`). The container probes `http://127.0.0.1:11434` when not using `APXV_CONTAINER_BIND` from inside the host network namespace; with default bridge networking, run Ollama on the host and map access (e.g. `extra_hosts: host.docker.internal:host-gateway` on Linux, or publish Ollama to the host loopback). |
| **Compose sidecar** | Add an `ollama` service to a local override compose file and point `OLLAMA_HOST` at that service in a future profile; until then, host Ollama is the supported team path. |
| **Skip at bootstrap** | `apxv_bootstrap --skip-ollama --skip-voice` (Docker install scripts default to skip optional integrations). Repair later from Settings → **Repair integrations** or `POST /api/v2/integrations/repair`. |

Voice (Vosk) model files live on the mounted `./managed` volume after `python -m scripts.setup_voice` or bootstrap step 7.

## Air-gap note

Build the image once online, save/load the image tarball, run offline with volumes on local disk. See [AIR-GAP-INSTALL.md](AIR-GAP-INSTALL.md).