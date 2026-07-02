# Docker Deployment

Run APXV1 as a local API service for team/company use.

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

APXV1 binds inside the container on `0.0.0.0:8741` (Docker-only via `APX_CONTAINER_BIND=1`). Host access is still localhost-only via compose port mapping.

## First-time setup in container

On first start with **empty volumes**, the entrypoint runs `setup_first_run --skip-zk` (ZK keys are baked into the image at build time).

Get your API key (v1.2.1+):

1. Read the hint file on the mounted volume: `managed/config/OPERATOR-KEY-default-operator.txt`
2. Or scan container logs: `docker logs apx-v1 2>&1 | findstr /i "API KEY"`

Save the key and delete the hint file after copying if desired. See [LOCAL-API.md](LOCAL-API.md) for auth details.

Create additional keys after start (accepted immediately without restarting the API):

```bash
docker exec apx-v1 python -m scripts.apx_ctl api-key create team-api --save-hint
```

The hint is written to `managed/config/OPERATOR-KEY-team-api.txt` on the mounted volume.

## Volumes (important)

`docker-compose.yml` mounts:

| Host path | Purpose |
|-----------|---------|
| `./managed` | Artifacts, config, audit, store |
| `./rust/apx-circuits/keys` | Governance ZK keys |
| `./rust/apx-zk/keys` | Entity ZK keys |

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
docker exec apx-v1 python -m scripts.apx_ctl backup-create
```

Backups land in `managed/backups/` on the mounted volume.

## Run pipeline inside container

```bash
docker exec apx-v1 python -m scripts.run_apx --attest
docker exec apx-v1 python -m scripts.verify_attestation --real-zk
```

## Troubleshooting

**`container name "/apx-v1" is already in use`**

Only one APXV1 API per host on port 8741. Remove the stale container, then start again:

```bash
docker rm -f apx-v1
docker compose up -d
```

`install-docker.sh` and `install-docker.ps1` run this cleanup automatically (v1.2.2+; bash since v1.2.1). On Windows PowerShell, the PS1 script ignores benign `No such container` stderr from `docker rm` so a second install in the same clone completes without manual steps.

## Air-gap note

Build the image once online, save/load the image tarball, run offline with volumes on local disk. See [AIR-GAP-INSTALL.md](AIR-GAP-INSTALL.md).