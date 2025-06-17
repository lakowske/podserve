#!/bin/bash
set -e

# Set default environment variables
export APACHE_SERVER_NAME=${APACHE_SERVER_NAME:-"local.dev"}
export APACHE_SERVER_ADMIN=${APACHE_SERVER_ADMIN:-"admin@local.dev"}
export APACHE_DOCUMENT_ROOT=${APACHE_DOCUMENT_ROOT:-"/var/www/html"}
export SSL_ENABLED=${SSL_ENABLED:-"auto"}
export SSL_CERT_FILE=${SSL_CERT_FILE:-"/data/state/certificates/${APACHE_SERVER_NAME}/cert.pem"}
export SSL_KEY_FILE=${SSL_KEY_FILE:-"/data/state/certificates/${APACHE_SERVER_NAME}/privkey.pem"}
export SSL_CHAIN_FILE=${SSL_CHAIN_FILE:-"/data/state/certificates/${APACHE_SERVER_NAME}/fullchain.pem"}

echo "Starting Apache for domain: $APACHE_SERVER_NAME"
echo "Admin email: $APACHE_SERVER_ADMIN"

# Ensure Apache directories exist and have correct permissions
mkdir -p ${APACHE_RUN_DIR} ${APACHE_LOCK_DIR}
chown -R www-data:www-data ${APACHE_RUN_DIR} ${APACHE_LOCK_DIR}
chmod 755 ${APACHE_RUN_DIR} ${APACHE_LOCK_DIR}

# Setup WebDAV directories if enabled
if [ "$WEBDAV_ENABLED" = "true" ]; then
    echo "Setting up WebDAV..."
    WEBDAV_ROOT="/data/web/webdav"
    WEBDAV_LOCK_DIR="/var/lock/apache2/webdav"
    WEBDAV_PASSWORD_FILE="/etc/apache2/.webdav-digest"

    # Create WebDAV directories
    mkdir -p ${WEBDAV_ROOT} ${WEBDAV_LOCK_DIR}
    chown -R www-data:www-data ${WEBDAV_ROOT} ${WEBDAV_LOCK_DIR}
    chmod 755 ${WEBDAV_ROOT} ${WEBDAV_LOCK_DIR}

    # Create empty WebDAV password file if it doesn't exist
    if [ ! -f "$WEBDAV_PASSWORD_FILE" ]; then
        echo "Creating WebDAV authentication file..."
        # Create a default user for demonstration
        echo -n "admin:webdav:" > "$WEBDAV_PASSWORD_FILE"
        echo -n "admin:webdav:changeme" | md5sum | cut -d' ' -f1 >> "$WEBDAV_PASSWORD_FILE"
        chmod 644 "$WEBDAV_PASSWORD_FILE"
        chown www-data:www-data "$WEBDAV_PASSWORD_FILE"
        echo "WebDAV user 'admin' created with password 'changeme'"
    fi

    # Enable WebDAV configuration
    a2enconf webdav
    echo "WebDAV setup complete"
fi

# Setup Git repositories if enabled
if [ "$GITWEB_ENABLED" = "true" ]; then
    echo "Setting up Gitweb..."
    GIT_REPO_DIR="/data/web/git/repositories"
    mkdir -p "$GIT_REPO_DIR"
    chown -R www-data:www-data "$GIT_REPO_DIR"

    # Create sample repositories if they don't exist
    if [ ! -d "$GIT_REPO_DIR/sample.git" ]; then
        echo "Creating sample Git repository..."
        cd "$GIT_REPO_DIR"

        # Create a sample bare repository
        git init --bare sample.git
        chown -R www-data:www-data sample.git

        # Set repository description
        echo "Sample Git repository for testing Gitweb interface" > sample.git/description

        echo "Sample Git repository created at $GIT_REPO_DIR/sample.git"
    fi

    # Enable Gitweb configuration
    a2enconf gitweb
    echo "Gitweb setup complete"
fi

# Determine SSL configuration
ENABLE_SSL="false"
if [ "$SSL_ENABLED" = "true" ]; then
    ENABLE_SSL="true"
elif [ "$SSL_ENABLED" = "auto" ]; then
    # Auto-detect if certificates exist
    if [ -f "$SSL_CERT_FILE" ] && [ -f "$SSL_KEY_FILE" ] && [ -f "$SSL_CHAIN_FILE" ]; then
        ENABLE_SSL="true"
        echo "Auto-detected SSL certificates, enabling HTTPS"
    else
        echo "No SSL certificates found, running HTTP only"
    fi
elif [ "$SSL_ENABLED" = "false" ]; then
    echo "SSL explicitly disabled"
fi

# Configure SSL if enabled and certificates exist
if [ "$ENABLE_SSL" = "true" ]; then
    echo "Configuring SSL..."

    if [ -f "$SSL_CERT_FILE" ] && [ -f "$SSL_KEY_FILE" ] && [ -f "$SSL_CHAIN_FILE" ]; then
        echo "SSL certificates found at:"
        echo "  - Certificate: $SSL_CERT_FILE"
        echo "  - Private key: $SSL_KEY_FILE"
        echo "  - Chain file: $SSL_CHAIN_FILE"

        # Substitute environment variables in SSL virtual host configuration
        envsubst '${APACHE_SERVER_NAME} ${APACHE_SERVER_ADMIN} ${APACHE_DOCUMENT_ROOT} ${SSL_CERT_FILE} ${SSL_KEY_FILE} ${SSL_CHAIN_FILE} ${APACHE_LOG_DIR}' \
            < /etc/apache2/sites-available/ssl-vhost.conf > /etc/apache2/sites-available/000-default-ssl.conf

        # Enable SSL site and modules
        a2ensite 000-default-ssl
        a2enmod ssl rewrite headers

        echo "HTTPS virtual host configured"
    else
        echo "Warning: SSL requested but certificates not found:"
        echo "  - Certificate: $SSL_CERT_FILE (exists: $([ -f "$SSL_CERT_FILE" ] && echo yes || echo no))"
        echo "  - Private key: $SSL_KEY_FILE (exists: $([ -f "$SSL_KEY_FILE" ] && echo yes || echo no))"
        echo "  - Chain file: $SSL_CHAIN_FILE (exists: $([ -f "$SSL_CHAIN_FILE" ] && echo yes || echo no))"
        echo "Falling back to HTTP only"
    fi
fi

# Enable additional configurations
a2enconf apache-extra

# Ensure default HTTP site is enabled
a2ensite 000-default

# Test configuration
echo "Testing Apache configuration..."
apache2ctl configtest

# Start Apache in foreground
echo "Starting Apache HTTP Server..."
echo "Access your site at:"
echo "  - HTTP: http://$APACHE_SERVER_NAME"
if [ "$ENABLE_SSL" = "true" ]; then
    echo "  - HTTPS: https://$APACHE_SERVER_NAME"
fi
if [ "$WEBDAV_ENABLED" = "true" ]; then
    echo "  - WebDAV: https://$APACHE_SERVER_NAME/webdav/"
fi
if [ "$GITWEB_ENABLED" = "true" ]; then
    echo "  - Git: https://$APACHE_SERVER_NAME/git/"
fi

exec /usr/sbin/apache2ctl -D FOREGROUND