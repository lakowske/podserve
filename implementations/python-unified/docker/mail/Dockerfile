# Mail service container
FROM localhost/podserve-base:latest

# Switch to root for package installation
USER root

# Install mail server packages
RUN apt-get update && apt-get install -y \
    postfix \
    dovecot-core \
    dovecot-imapd \
    dovecot-pop3d \
    dovecot-lmtpd \
    dovecot-managesieved \
    && rm -rf /var/lib/apt/lists/*

# Create mail directories and set permissions
RUN mkdir -p /var/mail/vhosts /var/spool/postfix/private /var/spool/postfix/public \
    /etc/postfix/maps /etc/dovecot/conf.d && \
    chown -R postfix:postfix /var/spool/postfix && \
    chmod 755 /var/mail/vhosts && \
    chmod 755 /etc/postfix/maps && \
    chmod 755 /etc/dovecot/conf.d

# Stay as root for mail services (they need root permissions)
# USER podserve

# Service-specific entry point
CMD ["mail"]