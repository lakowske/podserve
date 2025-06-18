# Apache Service Configuration

## Key Components

**Base Image**: localhost/podserve-base:latest  
**Exposed Ports**: 80, 443

## Environment Variables

- `APACHE_SERVER_NAME`: Server hostname (default: "local.dev")
- `APACHE_SERVER_ADMIN`: Admin email (default: "admin@local.dev")
- `SSL_ENABLED`: SSL mode - "true", "false", or "auto" (default: "auto")
- `SSL_CERT_FILE`: Path to SSL certificate (default: "/data/state/certificates/{APACHE_SERVER_NAME}/cert.pem")
- `SSL_KEY_FILE`: Path to SSL private key (default: "/data/state/certificates/{APACHE_SERVER_NAME}/privkey.pem")
- `SSL_CHAIN_FILE`: Path to SSL chain file (default: "/data/state/certificates/{APACHE_SERVER_NAME}/fullchain.pem")
- `WEBDAV_ENABLED`: Enable WebDAV support (default: "true")
- `GITWEB_ENABLED`: Enable Gitweb interface (default: "true")

## Features

1. **SSL Support**: Auto-detects certificates when SSL_ENABLED="auto"
2. **WebDAV**: Creates WebDAV directory at /data/web/webdav with digest authentication
3. **Gitweb**: Serves Git repositories from /data/web/git/repositories

## Volume Mounts

- `/data/state/certificates`: SSL certificate storage
- `/data/web`: Web content root

## Startup Process

1. Creates required directories and sets permissions
2. Configures WebDAV with default user "admin:changeme" if enabled
3. Sets up Git repositories and sample repo if enabled
4. Auto-detects SSL certificates and configures HTTPS if available
5. Starts Apache in foreground mode with proper signal handling