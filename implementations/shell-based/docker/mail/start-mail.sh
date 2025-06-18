#!/bin/bash
set -e

# Set default environment variables
export MAIL_SERVER_NAME=${MAIL_SERVER_NAME:-"mail.local.dev"}
export MAIL_DOMAIN=${MAIL_DOMAIN:-"local.dev"}
export SSL_CERT_FILE=${SSL_CERT_FILE:-"/data/state/certificates/$MAIL_DOMAIN/cert.pem"}
export SSL_KEY_FILE=${SSL_KEY_FILE:-"/data/state/certificates/$MAIL_DOMAIN/privkey.pem"}
export SSL_CHAIN_FILE=${SSL_CHAIN_FILE:-"/data/state/certificates/$MAIL_DOMAIN/fullchain.pem"}

echo "Starting mail server for domain: $MAIL_DOMAIN"
echo "Server name: $MAIL_SERVER_NAME"

# Create log directories
mkdir -p /data/logs/mail
chown -R root:root /data/logs/mail

# Check for SSL certificates
SSL_ENABLED="false"
if [ -f "$SSL_CERT_FILE" ] && [ -f "$SSL_KEY_FILE" ] && [ -f "$SSL_CHAIN_FILE" ]; then
    SSL_ENABLED="true"
    echo "SSL certificates found, enabling TLS"
    echo "  - Certificate: $SSL_CERT_FILE"
    echo "  - Private key: $SSL_KEY_FILE"
    echo "  - Chain file: $SSL_CHAIN_FILE"
    
    # Copy certificates to a location Dovecot can read with proper permissions
    echo "Copying and fixing certificate permissions for Dovecot..."
    mkdir -p /etc/ssl/certs/dovecot
    cp "$SSL_CERT_FILE" /etc/ssl/certs/dovecot/cert.pem
    cp "$SSL_KEY_FILE" /etc/ssl/certs/dovecot/privkey.pem
    cp "$SSL_CHAIN_FILE" /etc/ssl/certs/dovecot/fullchain.pem
    
    # Set proper ownership and permissions for Dovecot
    chown root:dovecot /etc/ssl/certs/dovecot/privkey.pem
    chmod 640 /etc/ssl/certs/dovecot/privkey.pem
    chmod 644 /etc/ssl/certs/dovecot/cert.pem /etc/ssl/certs/dovecot/fullchain.pem
    
    # Update SSL file paths for Dovecot
    export SSL_CERT_FILE="/etc/ssl/certs/dovecot/cert.pem"
    export SSL_KEY_FILE="/etc/ssl/certs/dovecot/privkey.pem"
    export SSL_CHAIN_FILE="/etc/ssl/certs/dovecot/fullchain.pem"
    
    # Verify Dovecot can now read the private key
    if su dovecot -s /bin/sh -c "test -r '$SSL_KEY_FILE'"; then
        echo "✓ Dovecot can read private key file"
    else
        echo "✗ Dovecot still cannot read private key file"
        ls -la "$SSL_KEY_FILE"
    fi
else
    echo "Warning: SSL certificates not found, running without TLS"
    echo "  - Certificate: $SSL_CERT_FILE (exists: $([ -f "$SSL_CERT_FILE" ] && echo yes || echo no))"
    echo "  - Private key: $SSL_KEY_FILE (exists: $([ -f "$SSL_KEY_FILE" ] && echo yes || echo no))"
    echo "  - Chain file: $SSL_CHAIN_FILE (exists: $([ -f "$SSL_CHAIN_FILE" ] && echo yes || echo no))"
fi

# Process Postfix configuration template
envsubst '${MAIL_SERVER_NAME} ${MAIL_DOMAIN} ${SSL_CERT_FILE} ${SSL_KEY_FILE} ${SSL_CHAIN_FILE}' \
    < /etc/postfix/main.cf.template > /etc/postfix/main.cf

# Process Dovecot SSL configuration template after certificates are copied
if [ "$SSL_ENABLED" = "true" ]; then
    envsubst '${SSL_CERT_FILE} ${SSL_KEY_FILE} ${SSL_CHAIN_FILE}' \
        < /etc/dovecot/conf.d/10-ssl.conf.template > /etc/dovecot/conf.d/10-ssl.conf
else
    # Disable SSL in Dovecot if no certificates
    echo "ssl = no" > /etc/dovecot/conf.d/10-ssl.conf
fi

# Create an admin user for mail testing
echo "Creating admin user: admin@$MAIL_DOMAIN"
mkdir -p "/var/mail/vhosts/$MAIL_DOMAIN/admin/Maildir"
chown -R vmail:vmail "/var/mail/vhosts/$MAIL_DOMAIN"

# Create virtual mailbox map (path should match Dovecot mail_location)
echo "admin@$MAIL_DOMAIN    $MAIL_DOMAIN/admin/Maildir/" > /etc/postfix/vmailbox
postmap /etc/postfix/vmailbox

# Create virtual domains file (required for Postfix to accept mail for the domain)
echo "$MAIL_DOMAIN    OK" > /etc/postfix/virtual_domains
postmap /etc/postfix/virtual_domains

# Create virtual alias map (required for mail delivery)
echo "admin@$MAIL_DOMAIN    admin@$MAIL_DOMAIN" > /etc/postfix/virtual
postmap /etc/postfix/virtual

# Create admin user credentials (password: 'password')
# Generate proper password hash using doveadm
ADMIN_PASSWORD_HASH=$(doveadm pw -s SHA512-CRYPT -p password)
echo "admin@$MAIL_DOMAIN:$ADMIN_PASSWORD_HASH" > /etc/dovecot/users
chown root:dovecot /etc/dovecot/users
chmod 640 /etc/dovecot/users

echo "Admin user created with password 'password'"
echo ""
echo "Mail server configuration complete!"
echo "  - SMTP: port 25 (plain), 587 (TLS)"
echo "  - IMAP: port 143 (plain), 993 (TLS)"
echo "  - POP3: port 110 (plain), 995 (TLS)"
echo "  - Admin account: admin@$MAIL_DOMAIN (password: password)"

# Debug: Show final SSL environment variables
if [ "$SSL_ENABLED" = "true" ]; then
    echo "Final SSL configuration:"
    echo "  - SSL_CERT_FILE: $SSL_CERT_FILE"
    echo "  - SSL_KEY_FILE: $SSL_KEY_FILE"
    echo "  - SSL_CHAIN_FILE: $SSL_CHAIN_FILE"
fi

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf