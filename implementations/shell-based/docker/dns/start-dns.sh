#!/bin/bash
set -e

echo "Starting DNS forwarder configuration..."

# Format forwarders for BIND config
export DNS_FORWARDERS_FORMATTED=$(echo "$DNS_FORWARDERS" | sed 's/;/;\n        /g')

# Process configuration template
envsubst < /etc/bind/named.conf.options.template > /etc/bind/named.conf.options

# Set proper permissions
chown -R bind:bind /etc/bind /var/cache/bind /var/log/bind
chmod 644 /etc/bind/*.conf

# Check configuration
echo "Checking BIND configuration..."
if ! named-checkconf; then
    echo "ERROR: BIND configuration check failed"
    cat /etc/bind/named.conf.options
    exit 1
fi

echo "DNS forwarder configuration complete."

# Start BIND in foreground
echo "Starting BIND DNS forwarder..."
exec /usr/sbin/named -g -u bind