# Base image for PodServe Python implementation
FROM debian:12-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    curl \
    wget \
    ca-certificates \
    openssl \
    ssl-cert \
    net-tools \
    iproute2 \
    iputils-ping \
    dnsutils \
    gettext-base \
    sed \
    gawk \
    procps \
    psmisc \
    && rm -rf /var/lib/apt/lists/*

# Create podserve group and user
RUN groupadd -g 1000 podserve && \
    useradd -m -u 1000 -g 1000 podserve

# Install Claude Code CLI (skip if not available)
RUN curl -fsSL https://storage.googleapis.com/anthropic-public/claude-code/install.sh | bash || \
    echo "Claude Code CLI not available, skipping..."

# Create Python virtual environment as root
RUN python3 -m venv /opt/podserve-venv

# Install Python dependencies
COPY requirements.txt /tmp/
RUN /opt/podserve-venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/podserve-venv/bin/pip install -r /tmp/requirements.txt

# Copy Python framework
COPY src/podserve /opt/podserve

# Create standard directories
RUN mkdir -p /data/config /data/logs /data/state && \
    chown -R podserve:podserve /data

# Set environment
ENV PATH="/opt/podserve-venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/podserve-venv"
ENV PYTHONPATH="/opt"

# Set working directory
WORKDIR /opt

# Default user
USER podserve

# Default entrypoint
ENTRYPOINT ["python3", "/opt/podserve/__main__.py"]