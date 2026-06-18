# Docker Deployment

Run APXV1 as a local API service for team/company use.

## Quick start

```bash
docker compose up -d --build
curl http://127.0.0.1:8741/health
```

APXV1 binds inside the container on `0.0.0.0:8741` (Docker-only via `APX_CONTAINER_BIND=1`). Host access is still localhost-only via compose port mapping.

## First-time setup in container

On first start with **empty volumes**, the entrypoint runs `setup_first_run --skip-zk` (ZK keys are baked into the image at build time).

Get your API key from logs:

```bash
docker logs apx-v1 2>&1 | findstr /i "API KEY"
```

Or create one after start:

```bash
docker exec apx-v1 python -m scripts.apx_ctl api-key create team-api
```

## Volumes (important)

`docker-compose.yml` mounts:

| Host path | Purpose |
|-----------|---------|
| `./managed` | Artifacts, config, audit, store |
| `./rust/keys` | ZK proving/verification keys |

### Use fresh volumes for production-like deploys

Do **not** mount a developer `managed/` directory with a long audit history. That can show `degraded` health from prior local experiments.

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

## Air-gap note

Build the image once online, save/load the image tarball, run offline with volumes on local disk. See [AIR-GAP-INSTALL.md](AIR-GAP-INSTALL.md).