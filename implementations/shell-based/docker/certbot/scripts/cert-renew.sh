#!/bin/bash
set -e

# Load configuration
CONFIG_FILE="/data/config/certbot/config.yaml"
if [[ -f "$CONFIG_FILE" ]]; then
    eval $(python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
    for k, v in config.get('certbot', {}).items():
        print(f'export CERTBOT_{k.upper()}=\"{v}\"')
    ")
fi

DOMAIN="${CERTBOT_DOMAIN:-local.dev}"
METHOD="${CERTBOT_METHOD:-standalone}"

# Skip renewal for self-signed certificates
if [[ "$METHOD" == "self-signed" ]]; then
    echo "Self-signed certificates do not need renewal"
    exit 0
fi

echo "Attempting to renew certificates..."

# Run certbot renew
certbot renew --quiet --no-self-upgrade

# Copy renewed certificates if successful
if [[ -d "/etc/letsencrypt/live/$DOMAIN" ]]; then
    CERT_PATH="/data/state/certificates/$DOMAIN"
    mkdir -p "$CERT_PATH"
    cp -L "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_PATH/"
    cp -L "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$CERT_PATH/"
    cp -L "/etc/letsencrypt/live/$DOMAIN/cert.pem" "$CERT_PATH/"
    cp -L "/etc/letsencrypt/live/$DOMAIN/chain.pem" "$CERT_PATH/" 2>/dev/null || true
    
    # Set permissions
    chown -R 1000:1000 "$CERT_PATH"
    chmod 755 "$CERT_PATH"
    chmod 644 "$CERT_PATH"/*.pem
    chmod 600 "$CERT_PATH/privkey.pem"
    
    echo "Certificates renewed and copied to shared volume"
    
    # Touch a reload flag file for other services to detect
    touch /data/state/certificates/.reload-required
fi