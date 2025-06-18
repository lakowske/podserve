# DNS service container
FROM localhost/podserve-base:latest

# Switch to root for package installation
USER root

# Install BIND9 and DNS utilities
RUN apt-get update && apt-get install -y \
    bind9 \
    bind9utils \
    bind9-doc \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Create BIND directories and set permissions
RUN mkdir -p /etc/bind/zones /var/cache/bind /var/lib/bind /var/log/bind && \
    chown -R bind:bind /etc/bind /var/cache/bind /var/lib/bind /var/log/bind && \
    chmod -R 755 /etc/bind /var/cache/bind /var/lib/bind /var/log/bind && \
    chmod 775 /var/cache/bind

# Copy default BIND configuration files (will be overridden by templates)
RUN cp /etc/bind/named.conf.default-zones /etc/bind/named.conf.default-zones.backup

# Create named.conf.default-zones with minimal content
RUN echo '// Default zones for root servers\n\
zone "." {\n\
    type hint;\n\
    file "/usr/share/dns/root.hints";\n\
};\n\
\n\
// Zones for localhost\n\
zone "localhost" {\n\
    type master;\n\
    file "/etc/bind/db.local";\n\
};\n\
\n\
zone "127.in-addr.arpa" {\n\
    type master;\n\
    file "/etc/bind/db.127";\n\
};\n\
\n\
zone "0.in-addr.arpa" {\n\
    type master;\n\
    file "/etc/bind/db.0";\n\
};\n\
\n\
zone "255.in-addr.arpa" {\n\
    type master;\n\
    file "/etc/bind/db.255";\n\
};' > /etc/bind/named.conf.default-zones

# Create minimal RPZ zone file
RUN mkdir -p /etc/bind/zones && \
    touch /etc/bind/zones/db.rpz && \
    chown bind:bind /etc/bind/zones/db.rpz

# Stay as root for BIND (needs root permissions for port 53)
USER root

# Service-specific entry point
CMD ["dns"]