# Certbot service container
FROM localhost/podserve-base:latest

# Switch to root for package installation
USER root

# Install Certbot and OpenSSL
RUN apt-get update && apt-get install -y \
    certbot \
    openssl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Create Certbot directories and set permissions
RUN mkdir -p /etc/letsencrypt /var/lib/letsencrypt /var/log/letsencrypt \
             /data/state/certificates /data/state/certbot \
             /var/www/html/.well-known/acme-challenge && \
    chown -R root:root /etc/letsencrypt /var/lib/letsencrypt /var/log/letsencrypt \
                       /data/state/certificates /data/state/certbot && \
    chmod -R 755 /etc/letsencrypt /var/lib/letsencrypt /var/log/letsencrypt \
                 /data/state/certificates /data/state/certbot && \
    chown -R www-data:www-data /var/www/html 2>/dev/null || true && \
    chmod -R 755 /var/www/html

# Create webroot directory structure for HTTP-01 challenges
RUN mkdir -p /var/www/html/.well-known/acme-challenge && \
    chmod 755 /var/www/html/.well-known/acme-challenge && \
    chown www-data:www-data /var/www/html/.well-known/acme-challenge 2>/dev/null || true

# Create directory for renewal hooks
RUN mkdir -p /data/scripts && \
    chmod 755 /data/scripts

# Copy renewal hooks script (will be populated by template)
RUN touch /data/scripts/renewal-hooks.sh && \
    chmod +x /data/scripts/renewal-hooks.sh

# Create log directory for Certbot
RUN mkdir -p /data/logs && \
    touch /data/logs/certbot.log /data/logs/certbot-renewal.log /data/logs/certbot-health.log && \
    chmod 644 /data/logs/*.log

# Set up default Certbot configuration directory structure
RUN mkdir -p /etc/letsencrypt/renewal-hooks/pre \
             /etc/letsencrypt/renewal-hooks/post \
             /etc/letsencrypt/renewal-hooks/deploy && \
    chmod 755 /etc/letsencrypt/renewal-hooks/pre \
              /etc/letsencrypt/renewal-hooks/post \
              /etc/letsencrypt/renewal-hooks/deploy

# Create symlinks for renewal hooks
RUN ln -sf /data/scripts/renewal-hooks.sh /etc/letsencrypt/renewal-hooks/pre/podserve-pre.sh && \
    ln -sf /data/scripts/renewal-hooks.sh /etc/letsencrypt/renewal-hooks/post/podserve-post.sh && \
    ln -sf /data/scripts/renewal-hooks.sh /etc/letsencrypt/renewal-hooks/deploy/podserve-deploy.sh

# Ensure proper permissions for OpenSSL operations
RUN chmod 755 /usr/bin/openssl

# Create a simple script to test certificate validity
RUN echo '#!/bin/bash\n\
if [ -z "$1" ]; then\n\
    echo "Usage: $0 <certificate-file>"\n\
    exit 1\n\
fi\n\
\n\
if [ ! -f "$1" ]; then\n\
    echo "Certificate file not found: $1"\n\
    exit 1\n\
fi\n\
\n\
# Check if certificate expires within next 30 days\n\
if openssl x509 -checkend 2592000 -noout -in "$1"; then\n\
    echo "Certificate is valid for more than 30 days"\n\
    exit 0\n\
else\n\
    echo "Certificate expires within 30 days"\n\
    exit 1\n\
fi' > /usr/local/bin/check-cert-expiry

RUN chmod +x /usr/local/bin/check-cert-expiry

# Stay as root for Certbot operations (needs root for file permissions)
USER root

# Service-specific entry point
CMD ["certbot"]