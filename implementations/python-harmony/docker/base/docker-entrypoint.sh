#!/bin/bash
# Smart entrypoint for PodServe-Harmony services
# Handles developer-friendly permissions and service setup

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "${GREEN}[entrypoint]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[entrypoint]${NC} $1"
}

log_error() {
    echo -e "${RED}[entrypoint]${NC} $1"
}

# Detect if we're running as root
if [ "$(id -u)" = "0" ]; then
    log "Running as root - setting up developer group permissions"
    
    # Ensure developer group exists
    if ! getent group developer > /dev/null 2>&1; then
        log "Creating developer group with GID 1000"
        groupadd -g 1000 developer 2>/dev/null || log_warn "Could not create developer group"
    fi
    
    # Set umask so group members can write
    umask 002
    export UMASK=002
    
    # Ensure data directories have proper group permissions
    if [ -d "/data" ]; then
        log "Setting group permissions on /data"
        chgrp -R developer /data 2>/dev/null || log_warn "Could not change group ownership of /data"
        chmod -R g+rwX /data 2>/dev/null || log_warn "Could not set group permissions on /data"
        
        # Set setgid bit on directories so new files inherit group
        find /data -type d -exec chmod g+s {} \; 2>/dev/null || log_warn "Could not set setgid on directories"
    fi
else
    log "Running as user $(id -un) (UID: $(id -u), GID: $(id -g))"
    
    # Set umask for consistent file creation
    umask 002
    export UMASK=002
fi

# Export environment for child processes
export PODSERVE_UMASK=002

# Handle Python services specially
if [[ "$1" == "python"* ]] || [[ "$1" == *"podserve"* ]]; then
    log "Python service detected - setting Python environment"
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONUNBUFFERED=1
fi

# Log the command we're about to run
log "Executing: $@"

# Execute the actual command
exec "$@"