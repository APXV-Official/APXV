# APXV — Runbook: Deployment

> **Note:** For first-time setup, see [docs/QUICKSTART.md](../docs/QUICKSTART.md) and [docs/DOCKER.md](../docs/DOCKER.md).

**Purpose:** Guide for deploying APXV in production or staging environments.

---

## 1. Prerequisites

- Docker (recommended) or Python 3.9+
- Rust toolchain (only if building from source)
- Access to the `managed/` directories (artifacts, audit, keys)

---

## 2. Recommended Deployment Method: Docker

### 2.1 Build the Image

```bash
docker build -t apxv:latest .
```

### 2.2 Run the Container

```bash
docker-compose up -d --build
```

### 2.3 Verify Deployment

```bash
curl http://127.0.0.1:8741/health
docker logs apxv
# First start runs setup_first_run if needed, then apxv_serve
```

---

## 3. Alternative: Python Installation (Development / Staging)

```bash
pip install -e ".[dev]"
python -m scripts.setup_first_run
python -m scripts.run_apxv --attest
python -m scripts.verify_attestation --real-zk
```

---

## 4. Configuration

- All configuration is currently file-based under `managed/`
- No environment variables are required by default
- To change base path, set `APXV_BASE_PATH` environment variable (legacy `APX_BASE_PATH` still read)

---

## 5. Health Check

```bash
python -c "
from agents.artifact_provider import FileArtifactProvider
from agents.audit_logger import AuditLogger
print('Core components healthy')
"
```

---

## 6. Rollback

- Docker: `docker stop apxv && docker rm apxv && docker run ...` with previous image tag
- Python: Revert to previous git tag and reinstall

---

*Last updated: 2026-06-09*