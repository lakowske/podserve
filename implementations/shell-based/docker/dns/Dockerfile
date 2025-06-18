FROM localhost/podserve-base:latest

LABEL maintainer="PodServe Project"
LABEL description="DNS forwarder with BIND9"

# Install DNS server packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bind9 \
        bind9-utils \
        bind9-dnsutils \
        bind9-host \
        dnsutils \
    && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create bind directories
RUN mkdir -p /var/cache/bind /var/log/bind && \
    chown -R bind:bind /etc/bind /var/cache/bind /var/log/bind && \
    chmod 755 /var/log/bind

# Copy configuration files
COPY dns/config/named.conf.forwarding /etc/bind/named.conf
COPY dns/config/named.conf.options.forwarding /etc/bind/named.conf.options.template

# Copy startup script
COPY --chmod=755 dns/start-dns.sh /usr/local/bin/start-dns.sh

# Set environment variables with defaults
ENV DNS_FORWARDERS="8.8.8.8;8.8.4.4" \
    DNSSEC_ENABLED=no

# Expose DNS ports (UDP and TCP)
EXPOSE 53/udp 53/tcp

# Health check for DNS
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD dig @127.0.0.1 google.com A +short || exit 1

# Set working directory
WORKDIR /etc/bind

# Use startup script as default command
CMD ["/usr/local/bin/start-dns.sh"]