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

# Create a test user for smoke testing
echo "Creating test user: test@$MAIL_DOMAIN"
mkdir -p "/var/mail/vhosts/$MAIL_DOMAIN/test"
chown -R vmail:vmail "/var/mail/vhosts/$MAIL_DOMAIN"

# Create virtual mailbox map
echo "test@$MAIL_DOMAIN    $MAIL_DOMAIN/test/Maildir/" > /etc/postfix/vmailbox
postmap /etc/postfix/vmailbox

# Create test user credentials (password: 'password')
echo "test@$MAIL_DOMAIN:{SHA512-CRYPT}\$6\$rounds=5000\$GESr7nXL6mhzJBaV\$3RbAqV4P5YZJLNaWyf8c5J95urhzKxWkJpNGJO1Q0rKo5Y.q8hE6QV4C5vZ9X5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y" > /etc/dovecot/users
chown root:dovecot /etc/dovecot/users
chmod 640 /etc/dovecot/users

echo "Test user created with password 'password'"
echo ""
echo "Mail server configuration complete!"
echo "  - SMTP: port 25 (plain), 587 (TLS)"
echo "  - IMAP: port 143 (plain), 993 (TLS)"
echo "  - POP3: port 110 (plain), 995 (TLS)"
echo "  - Test account: test@$MAIL_DOMAIN (password: password)"

# Debug: Show final SSL environment variables
if [ "$SSL_ENABLED" = "true" ]; then
    echo "Final SSL configuration:"
    echo "  - SSL_CERT_FILE: $SSL_CERT_FILE"
    echo "  - SSL_KEY_FILE: $SSL_KEY_FILE"
    echo "  - SSL_CHAIN_FILE: $SSL_CHAIN_FILE"
fi

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf