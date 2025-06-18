#!/bin/bash
set -e

# Load configuration
CONFIG_FILE="/data/config/certbot/config.yaml"
if [[ -f "$CONFIG_FILE" ]]; then
    echo "Loading configuration from $CONFIG_FILE"
    eval $(python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
    for k, v in config.get('certbot', {}).items():
        print(f'export CERTBOT_{k.upper()}=\"{v}\"')
    ")
fi

# Set defaults
DOMAIN="${CERTBOT_DOMAIN:-local.dev}"
EMAIL="${CERTBOT_EMAIL:-admin@$DOMAIN}"
STAGING="${CERTBOT_STAGING:-false}"
METHOD="${CERTBOT_METHOD:-standalone}"

# Determine staging flag
STAGING_FLAG=""
if [[ "$STAGING" == "true" ]]; then
    STAGING_FLAG="--staging"
    echo "Using Let's Encrypt staging environment"
fi

# Check if certificates already exist
CERT_PATH="/data/state/certificates/$DOMAIN"
if [[ -f "$CERT_PATH/fullchain.pem" ]] && [[ -f "$CERT_PATH/privkey.pem" ]]; then
    echo "Certificates already exist for $DOMAIN"
    # Check expiration
    openssl x509 -checkend 604800 -noout -in "$CERT_PATH/fullchain.pem"
    if [[ $? -eq 0 ]]; then
        echo "Certificate is still valid for more than 7 days"
        exit 0
    else
        echo "Certificate will expire soon, attempting renewal"
    fi
fi

# Generate certificates based on method
case "$METHOD" in
    "standalone")
        echo "Using standalone method (requires port 80 to be free)"
        certbot certonly \
            --standalone \
            --agree-tos \
            --non-interactive \
            --email "$EMAIL" \
            --domains "$DOMAIN" \
            --cert-path "$CERT_PATH" \
            $STAGING_FLAG
        ;;
    "dns-cloudflare")
        echo "Using Cloudflare DNS method"
        certbot certonly \
            --dns-cloudflare \
            --dns-cloudflare-credentials /data/config/certbot/cloudflare.ini \
            --agree-tos \
            --non-interactive \
            --email "$EMAIL" \
            --domains "$DOMAIN,*.$DOMAIN" \
            --cert-path "$CERT_PATH" \
            $STAGING_FLAG
        ;;
    "webroot")
        echo "Using webroot method"
        certbot certonly \
            --webroot \
            --webroot-path /data/web/html \
            --agree-tos \
            --non-interactive \
            --email "$EMAIL" \
            --domains "$DOMAIN" \
            --cert-path "$CERT_PATH" \
            $STAGING_FLAG
        ;;
    "self-signed")
        echo "Generating self-signed certificate"
        mkdir -p "$CERT_PATH"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$CERT_PATH/privkey.pem" \
            -out "$CERT_PATH/fullchain.pem" \
            -subj "/C=US/ST=State/L=City/O=PodServe/CN=*.$DOMAIN"
        cp "$CERT_PATH/fullchain.pem" "$CERT_PATH/cert.pem"
        echo "Self-signed certificate generated"
        ;;
    *)
        echo "Unknown method: $METHOD"
        exit 1
        ;;
esac

# Copy certificates to the shared volume
if [[ "$METHOD" != "self-signed" ]] && [[ -d "/etc/letsencrypt/live/$DOMAIN" ]]; then
    echo "Copying certificates to shared volume"
    mkdir -p "$CERT_PATH"
    cp -L "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_PATH/"
    cp -L "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$CERT_PATH/"
    cp -L "/etc/letsencrypt/live/$DOMAIN/cert.pem" "$CERT_PATH/"
    cp -L "/etc/letsencrypt/live/$DOMAIN/chain.pem" "$CERT_PATH/" 2>/dev/null || true
fi

# Set permissions
chown -R 1000:1000 "$CERT_PATH"
chmod 755 "$CERT_PATH"
chmod 644 "$CERT_PATH"/*.pem
chmod 600 "$CERT_PATH/privkey.pem"

echo "Certificate initialization complete"