FROM localhost/podserve-base:latest

LABEL maintainer="PodServe Project"
LABEL description="Certbot container for Let's Encrypt certificate management"

# Install Certbot and plugins
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        certbot \
        python3-certbot-dns-cloudflare \
        python3-certbot-dns-route53 \
        python3-certbot-dns-google \
        cron \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create certbot directories
RUN mkdir -p \
    /etc/letsencrypt \
    /var/lib/letsencrypt \
    /var/log/letsencrypt \
    /data/state/certificates \
    /data/config/certbot

# Copy certificate management scripts
COPY --chmod=755 certbot/scripts/ /usr/local/bin/

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command - run in cron mode
CMD ["cron"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["/usr/local/bin/entrypoint.sh", "check"]

# Run as podserve user
USER podserve

# Volumes
VOLUME ["/data/state/certificates", "/data/config/certbot", "/data/logs"]