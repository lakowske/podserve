#!/bin/bash
# DNS service entrypoint for PodServe-Harmony
# Extends base entrypoint with DNS-specific initialization

# Source the base entrypoint functions
source /usr/local/bin/docker-entrypoint.sh

# DNS-specific initialization
dns_init() {
    echo -e "${GREEN}[dns-init]${NC} Initializing DNS service"
    
    # Ensure DNS directories exist with proper permissions
    mkdir -p /data/state/dns/{zones,cache}
    mkdir -p /data/config/dns
    mkdir -p /data/logs
    
    # Ensure we can write to DNS directories
    if [ ! -w /data/state/dns ]; then
        echo -e "${YELLOW}[dns-init]${NC} Warning: /data/state/dns not writable"
    fi
    
    echo -e "${GREEN}[dns-init]${NC} DNS service initialization complete"
}

# Override the service initialization
service_init() {
    dns_init
}

# Check if this is a DNS service command
if [[ "$1" =~ python3.*dns ]] || [[ "$*" =~ podserve.*dns ]]; then
    echo -e "${GREEN}[entrypoint]${NC} DNS service detected - running DNS initialization"
    service_init
fi

# Continue with base entrypoint logic
main_entrypoint "$@"