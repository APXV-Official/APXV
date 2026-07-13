# APXV — Multi-stage Docker build
# Builds Rust prover/verifier binaries only — NO proving keys in the image (v1.3 sovereign).

# ============================================
# Stage 1: Build Rust binaries
# ============================================
FROM rust:1.85-slim AS rust-builder

WORKDIR /app/rust

COPY rust/Cargo.toml rust/Cargo.lock ./
COPY rust/apxv-circuits ./apxv-circuits
COPY rust/apxv-zk ./apxv-zk

# Binaries only — sovereign bootstrap generates keys on operator volumes at runtime.
RUN cargo build --release -p apxv-circuits -p apxv-zk

# ============================================
# Stage 2: Python runtime
# ============================================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY agents ./agents
COPY scripts ./scripts
COPY governance-libraries ./governance-libraries

RUN pip install --no-cache-dir -e .

COPY --from=rust-builder /app/rust/target/release/apxv-circuits /usr/local/bin/apxv-circuits
COPY --from=rust-builder /app/rust/target/release/apxv-zk /usr/local/bin/apxv-zk
RUN chmod +x /usr/local/bin/apxv-circuits /usr/local/bin/apxv-zk

COPY managed/rules ./managed/rules
COPY managed/workflows ./managed/workflows
COPY managed/knowledge ./managed/knowledge

# Empty key dirs — populated via volume mounts + apxv_bootstrap on first start.
RUN mkdir -p /app/managed/artifacts /app/managed/audit /app/managed/backups \
    /app/managed/config /app/managed/store/blobs \
    /app/rust/apxv-circuits/keys /app/rust/apxv-zk/keys

ENV PYTHONUNBUFFERED=1
ENV APXV_BASE_PATH=/app
ENV APXV_CONTAINER_BIND=1

EXPOSE 8741

CMD ["python", "-m", "scripts.docker_entrypoint"]