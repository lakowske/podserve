#!/bin/bash
# Build script for PodServe Python implementation

set -e

cd "$(dirname "$0")"

# Default service to build
SERVICE=${1:-all}
TAG=${2:-latest}

echo "Building PodServe Python implementation..."

# Build base image first
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "base" ]; then
    echo "Building base image..."
    # Copy Python source to build context
    cp -r ../src base/
    
    # Create requirements.txt from pyproject.toml dependencies
    cat > base/requirements.txt << EOF
jinja2>=3.0.0
pyyaml>=6.0
requests>=2.28.0
watchdog>=2.0.0
EOF
    
    podman build -t localhost/podserve-base:$TAG base/
    
    # Clean up
    rm -rf base/src
    
    echo "Base image built successfully"
fi

# Build service images
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "mail" ]; then
    echo "Building mail service..."
    podman build -t localhost/podserve-mail:$TAG mail/
    echo "Mail service built successfully"
fi

if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "apache" ]; then
    echo "Building apache service..."
    if [ -d apache ]; then
        podman build -t localhost/podserve-apache:$TAG apache/
        echo "Apache service built successfully"
    else
        echo "Apache service not yet implemented"
    fi
fi

if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "dns" ]; then
    echo "Building DNS service..."
    if [ -d dns ]; then
        podman build -t localhost/podserve-dns:$TAG dns/
        echo "DNS service built successfully"
    else
        echo "DNS service not yet implemented"
    fi
fi

if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "certbot" ]; then
    echo "Building Certbot service..."
    if [ -d certbot ]; then
        podman build -t localhost/podserve-certbot:$TAG certbot/
        echo "Certbot service built successfully"
    else
        echo "Certbot service not yet implemented"
    fi
fi

echo "Build completed!"