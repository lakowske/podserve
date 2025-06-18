FROM localhost/podserve-base:latest

LABEL maintainer="PodServe Project"
LABEL description="Apache web server with SSL support via certbot certificates"

# Install Apache and additional packages not in base
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apache2 \
        apache2-utils \
        git \
        gitweb \
    && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Enable required Apache modules
RUN a2enmod ssl && \
    a2enmod rewrite && \
    a2enmod headers && \
    a2enmod deflate && \
    a2enmod dav && \
    a2enmod dav_fs && \
    a2enmod dav_lock && \
    a2enmod auth_digest && \
    a2enmod cgi

# Create Apache directories and set permissions
RUN mkdir -p \
    /var/www/html \
    /var/www/webdav \
    /var/git/repositories \
    /data/web/html \
    /data/web/webdav \
    /data/web/git/repositories && \
    # Set ownership for web directories
    chown -R www-data:www-data /var/www /data/web && \
    chmod 755 /var/www/webdav /data/web/webdav

# Copy configuration files to appropriate locations
COPY apache/config/000-default.conf /etc/apache2/sites-available/
COPY apache/config/ssl-vhost.conf /etc/apache2/sites-available/
COPY apache/config/apache-extra.conf /etc/apache2/conf-available/
COPY apache/config/apache-shutdown.conf /etc/apache2/conf-available/
COPY apache/config/webdav.conf /etc/apache2/conf-available/
COPY apache/config/gitweb.conf /etc/apache2/conf-available/
COPY apache/content/ /var/www/html/

# Copy startup script and shutdown script
COPY --chmod=755 apache/start-apache.sh /usr/local/bin/start-apache.sh
COPY --chmod=755 apache/graceful-stop.sh /usr/local/bin/graceful-stop.sh

# Set environment variables with defaults
ENV APACHE_SERVER_NAME=local.dev \
    APACHE_SERVER_ADMIN=admin@local.dev \
    APACHE_LOG_DIR=/dev/stdout \
    APACHE_RUN_USER=www-data \
    APACHE_RUN_GROUP=www-data \
    APACHE_PID_FILE=/var/run/apache2/apache2.pid \
    APACHE_RUN_DIR=/var/run/apache2 \
    APACHE_LOCK_DIR=/var/lock/apache2 \
    SSL_ENABLED=auto \
    WEBDAV_ENABLED=true \
    GITWEB_ENABLED=true

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Set working directory
WORKDIR /var/www/html

# Use startup script as default command
CMD ["/usr/local/bin/start-apache.sh"]

# Volumes
VOLUME ["/data/state/certificates", "/data/web"]