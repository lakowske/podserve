#!/bin/bash
# Certificate service specific entrypoint

set -e

echo "Starting PodServe-Harmony Certificate Service"

# Ensure certificate directories exist with proper permissions
mkdir -p /data/state/certificates /data/config/certificates
chmod 755 /data/state/certificates /data/config/certificates

# Set default environment variables if not provided
export DOMAIN=${DOMAIN:-lab.sethlakowske.com}
export CERTBOT_EMAIL=${CERTBOT_EMAIL:-admin@${DOMAIN}}
export CERTBOT_METHOD=${CERTBOT_METHOD:-self-signed}
export CERTBOT_STAGING=${CERTBOT_STAGING:-false}

echo "Certificate service configuration:"
echo "  Domain: $DOMAIN"
echo "  Email: $CERTBOT_EMAIL"
echo "  Method: $CERTBOT_METHOD"
echo "  Staging: $CERTBOT_STAGING"

# Call the base entrypoint
exec /usr/local/bin/docker-entrypoint.sh "$@"