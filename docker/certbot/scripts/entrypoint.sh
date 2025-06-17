#!/bin/bash
set -e

# Create configuration from environment variables or use defaults
mkdir -p /data/config/certbot

# Use environment variables if provided, otherwise use defaults
DOMAIN="${CERTBOT_DOMAIN:-local.dev}"
EMAIL="${CERTBOT_EMAIL:-admin@$DOMAIN}"
STAGING="${CERTBOT_STAGING:-false}"
METHOD="${CERTBOT_METHOD:-self-signed}"

# Create/update configuration file with current environment
cat > /data/config/certbot/config.yaml << EOC
certbot:
  domain: $DOMAIN
  email: $EMAIL
  staging: $STAGING
  method: $METHOD  # Options: standalone, dns-cloudflare, webroot, self-signed
  
  # For dns-cloudflare method, create cloudflare.ini with:
  # dns_cloudflare_email = your-email@example.com
  # dns_cloudflare_api_key = your-api-key
EOC
echo "Created/updated configuration at /data/config/certbot/config.yaml for domain: $DOMAIN"

# Run the command
case "$1" in
    "init")
        exec /usr/local/bin/cert-init.sh
        ;;
    "renew")
        exec /usr/local/bin/cert-renew.sh
        ;;
    "cron")
        echo "Starting certbot in cron mode"
        # Add cron job for renewal
        echo "0 2 * * * /usr/local/bin/cert-renew.sh >> /data/logs/certbot-cron.log 2>&1" | crontab -
        # Run initial check
        /usr/local/bin/cert-init.sh
        # Start cron in foreground
        cron -f
        ;;
    "check")
        # Check certificate status
        DOMAIN="${CERTBOT_DOMAIN:-local.dev}"
        CERT_PATH="/data/state/certificates/$DOMAIN/fullchain.pem"
        if [[ -f "$CERT_PATH" ]]; then
            echo "Certificate information for $DOMAIN:"
            openssl x509 -in "$CERT_PATH" -noout -subject -issuer -dates
            echo ""
            echo -n "Valid for: "
            openssl x509 -in "$CERT_PATH" -checkend 0 >/dev/null 2>&1 && echo "YES" || echo "NO"
            echo -n "Expires within 30 days: "
            openssl x509 -in "$CERT_PATH" -checkend 2592000 >/dev/null 2>&1 && echo "NO" || echo "YES"
        else
            echo "No certificate found at $CERT_PATH"
        fi
        ;;
    *)
        # Pass through to shell
        exec "$@"
        ;;
esac