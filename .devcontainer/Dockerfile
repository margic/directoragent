FROM mcr.microsoft.com/devcontainers/base:ubuntu

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget build-essential pkg-config git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python handled by devcontainer feature (3.12)
# Install NATS CLI (optional)
RUN curl -L https://github.com/nats-io/natscli/releases/download/v0.1.5/nats-0.1.5-amd64.deb -o /tmp/natscli.deb \
    && apt-get update && apt-get install -y /tmp/natscli.deb || true

WORKDIR /workspace
