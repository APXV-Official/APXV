# APXV1 — Multi-stage Docker build
# Builds the Rust prover/verifier and packages the Python governed runtime

# ============================================
# Stage 1: Build Rust binary
# ============================================
FROM rust:1.85-slim AS rust-builder

WORKDIR /app/rust

# Copy workspace crates needed for Rust build (better cache)
COPY rust/Cargo.toml rust/Cargo.lock ./
COPY rust/apx-circuits ./apx-circuits
COPY rust/apx-zk ./apx-zk

# Build governance + entity provers and generate ZK trusted-setup keys in the image
RUN cargo build --release -p apx-circuits -p apx-zk \
    && cd apx-circuits \
    && ../target/release/apx-circuits setup redaction \
    && ../target/release/apx-circuits setup rule-binding \
    && ../target/release/apx-circuits setup pipeline \
    && cd ../apx-zk \
    && ../target/release/apx-zk setup normalization \
    && ../target/release/apx-zk setup core-redaction \
    && ../target/release/apx-zk setup compliance \
    && ../target/release/apx-zk setup threat \
    && ../target/release/apx-zk setup voice-redaction \
    && ../target/release/apx-zk setup redaction-v1 \
    && ../target/release/apx-zk setup merkle-inclusion \
    && ../target/release/apx-zk setup batch-merkle

# ============================================
# Stage 2: Python runtime
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python package
COPY pyproject.toml ./
COPY agents ./agents
COPY scripts ./scripts

# Install the Python package
RUN pip install --no-cache-dir -e .

# Copy the compiled Rust binary and ZK keys from the builder stage
COPY --from=rust-builder /app/rust/target/release/apx-circuits /usr/local/bin/apx-circuits
COPY --from=rust-builder /app/rust/target/release/apx-zk /usr/local/bin/apx-zk
COPY --from=rust-builder /app/rust/apx-circuits/keys ./rust/apx-circuits/keys
COPY --from=rust-builder /app/rust/apx-zk/keys ./rust/apx-zk/keys

# Make the binaries executable
RUN chmod +x /usr/local/bin/apx-circuits /usr/local/bin/apx-zk

# Governance templates (runtime state comes from mounted volumes)
COPY managed/rules ./managed/rules
COPY managed/workflows ./managed/workflows
COPY managed/knowledge ./managed/knowledge

# Create runtime directories (populated via volumes at deploy time)
RUN mkdir -p /app/managed/artifacts /app/managed/audit /app/managed/backups \
    /app/managed/config /app/managed/store/blobs \
    /app/rust/apx-circuits/keys /app/rust/apx-zk/keys

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APX_BASE_PATH=/app

EXPOSE 8741

# Default: bootstrap if needed, then local API server
CMD ["python", "-m", "scripts.docker_entrypoint"]