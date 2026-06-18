# APXV1 — Multi-stage Docker build
# Builds the Rust prover/verifier and packages the Python governed runtime

# ============================================
# Stage 1: Build Rust binary
# ============================================
FROM rust:1.85-slim AS rust-builder

WORKDIR /app/rust

# Copy only the files needed for Rust build (better cache)
COPY rust/Cargo.toml rust/Cargo.lock ./
COPY rust/src ./src
COPY rust/circuits ./circuits

# Build the Rust binary and generate ZK trusted-setup keys in the image
RUN cargo build --release \
    && ./target/release/apx-circuits setup redaction \
    && ./target/release/apx-circuits setup rule-binding \
    && ./target/release/apx-circuits setup pipeline

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
COPY --from=rust-builder /app/rust/keys ./rust/keys

# Make the binary executable
RUN chmod +x /usr/local/bin/apx-circuits

# Governance templates (runtime state comes from mounted volumes)
COPY managed/rules ./managed/rules
COPY managed/workflows ./managed/workflows
COPY managed/knowledge ./managed/knowledge

# Create runtime directories (populated via volumes at deploy time)
RUN mkdir -p /app/managed/artifacts /app/managed/audit /app/managed/backups \
    /app/managed/config /app/managed/store/blobs /app/rust/keys

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APX_BASE_PATH=/app

EXPOSE 8741

# Default: bootstrap if needed, then local API server
CMD ["python", "-m", "scripts.docker_entrypoint"]