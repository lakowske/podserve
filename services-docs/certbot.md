# Certbot Service Configuration

## Key Components

**Base Image**: localhost/podserve-base:latest  
**Purpose**: Let's Encrypt certificate management

## Environment Variables

- `CERTBOT_DOMAIN`: Domain to manage certificates for (default: "local.dev")
- `CERTBOT_EMAIL`: Email for Let's Encrypt registration (default: "admin@{domain}")
- `CERTBOT_STAGING`: Use Let's Encrypt staging environment (default: "false")
- `CERTBOT_METHOD`: Certificate method - "standalone", "dns-cloudflare", "webroot", or "self-signed" (default: "self-signed")

## Operating Modes

1. **init**: Initial certificate generation
2. **renew**: Certificate renewal check
3. **cron**: Automated renewal mode with daily checks at 2 AM
4. **check**: Display certificate status and expiration

## Configuration

Creates `/data/config/certbot/config.yaml` with current settings. For DNS plugins, additional credential files are required (e.g., cloudflare.ini).

## Volume Mounts

- `/data/state/certificates`: Certificate storage location
- `/data/config/certbot`: Configuration files
- `/data/logs`: Certbot logs

## Certificate Storage

Certificates are stored in `/data/state/certificates/{domain}/` with standard Let's Encrypt naming:
- cert.pem: Domain certificate
- privkey.pem: Private key
- fullchain.pem: Full certificate chain