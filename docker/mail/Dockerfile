FROM localhost/podserve-base:latest

LABEL maintainer="PodServe Project"
LABEL description="Mail server with Dovecot and Postfix with SSL support via shared certificates"

# Install mail server packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postfix \
        dovecot-core \
        dovecot-imapd \
        dovecot-pop3d \
        dovecot-lmtpd \
        mailutils \
        supervisor \
        netcat-openbsd \
    && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create mail user and directories
RUN groupadd -g 5000 vmail && \
    useradd -r -u 5000 -g vmail -d /var/mail/vhosts -s /bin/false vmail && \
    mkdir -p /var/mail/vhosts && \
    chown -R vmail:vmail /var/mail/vhosts && \
    chmod 755 /var/mail/vhosts

# Generate DH parameters for Dovecot
RUN openssl dhparam -out /etc/dovecot/dh.pem 2048

# Copy configuration files
COPY mail/config/main.cf /etc/postfix/main.cf.template
COPY mail/config/master.cf /etc/postfix/master.cf
COPY mail/config/dovecot.conf /etc/dovecot/dovecot.conf
COPY mail/config/10-ssl.conf /etc/dovecot/conf.d/10-ssl.conf.template
COPY mail/config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY --chmod=755 mail/start-mail.sh /usr/local/bin/start-mail.sh

# Set environment variables with defaults
ENV MAIL_SERVER_NAME=mail.local.dev \
    MAIL_DOMAIN=local.dev

# Expose mail ports
EXPOSE 25 143 110 993 995 587

# Health check for SMTP
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD echo "QUIT" | nc -w 1 localhost 25 || exit 1

# Set working directory
WORKDIR /var/mail

# Use startup script as default command
CMD ["/usr/local/bin/start-mail.sh"]

# Volumes
VOLUME ["/data/state/certificates", "/var/mail/vhosts"]