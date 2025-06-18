FROM debian:12-slim

LABEL maintainer="PodServe Project"
LABEL description="Base image with common packages for PodServe services"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC

# Install common system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Basic utilities
        curl \
        wget \
        ca-certificates \
        gnupg \
        lsb-release \
        # Network tools
        net-tools \
        iproute2 \
        iputils-ping \
        dnsutils \
        telnet \
        # Python and development
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        # SSL/Security
        openssl \
        ssl-cert \
        # Text processing
        gettext-base \
        sed \
        gawk \
        # Process management
        procps \
        psmisc \
        # Filesystem tools
        rsync \
        # Timezone data
        tzdata \
    && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    # Create common directories
    mkdir -p /data/config /data/logs /data/state && \
    # Set timezone
    ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# Create a common non-root user for services
RUN groupadd -g 1000 podserve && \
    useradd -u 1000 -g 1000 -m -s /bin/bash podserve

# Install common Python packages via apt (PEP 668 compliance)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-yaml \
        python3-jinja2 \
        python3-requests \
        python3-cryptography \
        python3-setuptools \
        python3-wheel \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Add health check script
COPY --chmod=755 base/healthcheck.sh /usr/local/bin/healthcheck.sh

# Set up volume mount points
VOLUME ["/data/config", "/data/logs", "/data/state"]

# Default working directory
WORKDIR /opt

# Default command (services should override)
CMD ["/bin/bash"]