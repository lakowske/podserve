# Apache service container
FROM localhost/podserve-base:latest

# Switch to root for package installation
USER root

# Install Apache and required modules
RUN apt-get update && apt-get install -y \
    apache2 \
    apache2-utils \
    && rm -rf /var/lib/apt/lists/*

# Create web directories and set permissions
RUN mkdir -p /data/web/html /var/log/apache2 && \
    chmod 755 /data/web/html && \
    chown -R www-data:www-data /var/log/apache2

# Disable default Apache site and enable required modules
RUN a2dissite 000-default && \
    a2enmod rewrite headers

# Create Apache configuration directories
RUN mkdir -p /etc/apache2/sites-available /etc/apache2/sites-enabled

# Stay as root for Apache (needs root permissions)
# USER podserve

# Service-specific entry point
CMD ["apache"]