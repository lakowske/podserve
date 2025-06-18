# Mail Service Configuration

## Key Components

**Base Image**: localhost/podserve-base:latest  
**Services**: Postfix (SMTP) + Dovecot (IMAP/POP3)  
**Exposed Ports**: 25, 143, 110, 993, 995, 587

## Environment Variables

- `MAIL_SERVER_NAME`: Mail server hostname (default: "mail.local.dev")
- `MAIL_DOMAIN`: Mail domain (default: "local.dev")
- `SSL_CERT_FILE`: Path to SSL certificate (default: "/data/state/certificates/{MAIL_DOMAIN}/cert.pem")
- `SSL_KEY_FILE`: Path to SSL private key (default: "/data/state/certificates/{MAIL_DOMAIN}/privkey.pem")
- `SSL_CHAIN_FILE`: Path to SSL chain file (default: "/data/state/certificates/{MAIL_DOMAIN}/fullchain.pem")

## Features

1. **Virtual Mail Users**: Uses vmail user (UID/GID 5000) for virtual mailboxes
2. **SSL/TLS Support**: Auto-detects certificates and enables TLS on all protocols
3. **Default Admin User**: Creates admin@{MAIL_DOMAIN} with password "password"
4. **Maildir Format**: Stores emails in /var/mail/vhosts/{domain}/{user}/Maildir/

## Startup Process

1. Copies SSL certificates with proper permissions for Dovecot access
2. Configures Postfix with virtual domains and mailboxes
3. Sets up Dovecot with password authentication
4. Creates admin user with SHA512-CRYPT password hash
5. Starts both services via supervisord

## Volume Mounts

- `/data/state/certificates`: SSL certificate storage
- `/var/mail/vhosts`: Virtual mailbox storage

## Access Ports

- SMTP: 25 (plain), 587 (STARTTLS)
- IMAP: 143 (plain), 993 (SSL/TLS)
- POP3: 110 (plain), 995 (SSL/TLS)