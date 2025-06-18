#!/bin/bash
# Build script for PodServe-Harmony developer-friendly containers
# Uses host UID/GID to avoid permission issues

set -e

# Get host UID/GID
USER_UID=${USER_UID:-$(id -u)}
USER_GID=${USER_GID:-$(id -g)}
USERNAME=${USERNAME:-developer}

# Build arguments
BUILD_ARGS=(
    "--build-arg" "USER_UID=${USER_UID}"
    "--build-arg" "USER_GID=${USER_GID}"
    "--build-arg" "USERNAME=${USERNAME}"
)

# Default to latest tag
TAG=${TAG:-latest}

echo "Building PodServe-Harmony with UID=${USER_UID}, GID=${USER_GID}, USER=${USERNAME}"

# Service to build
SERVICE=${1:-all}

# Function to build a service
build_service() {
    local service_name=$1
    local dockerfile=${2:-Dockerfile.developer}
    
    echo "Building ${service_name} service..."
    
    if [ -d "${service_name}" ]; then
        pushd "${service_name}" > /dev/null
        
        # Use developer-friendly Dockerfile
        if [ -f "${dockerfile}" ]; then
            podman build "${BUILD_ARGS[@]}" -f "${dockerfile}" -t "localhost/podserve-harmony-${service_name}:${TAG}" .
        else
            echo "Error: ${dockerfile} not found"
            exit 1
        fi
        
        popd > /dev/null
        echo "✅ Built podserve-harmony-${service_name}:${TAG}"
    else
        echo "Error: Directory ${service_name} not found"
        exit 1
    fi
}

# Build base image first
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "base" ]; then
    echo "Building base image..."
    # Copy source and project config to build context
    rm -rf base/src base/pyproject.toml 2>/dev/null || true
    cp -r ../src base/
    cp ../pyproject.toml base/
    build_service "base" "Dockerfile.developer"
    rm -rf base/src base/pyproject.toml
fi

# Build certificates service
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "certificates" ]; then
    build_service "certificates" "Dockerfile.developer"
fi

# Build DNS service
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "dns" ]; then
    build_service "dns" "Dockerfile.developer"
fi

# Future services will be added here as they're implemented

echo ""
echo "Build complete! Container images:"
podman images | grep "localhost/podserve-harmony-" | grep "${TAG}"

echo ""
echo "Quick start commands:"
echo "  # Test certificates service in isolation:"
echo "  podman run --rm -e LOG_LEVEL=DEBUG localhost/podserve-harmony-certificates:${TAG}"
echo ""
echo "  # Test DNS service in isolation:"
echo "  podman run --rm -p 53:53/udp -e LOG_LEVEL=DEBUG localhost/podserve-harmony-dns:${TAG}"
echo ""
echo "  # Run health checks:"
echo "  podman run --rm localhost/podserve-harmony-certificates:${TAG} /usr/local/bin/health-check.sh certificates"
echo "  podman run --rm localhost/podserve-harmony-dns:${TAG} /usr/local/bin/health-check.sh dns"
echo ""
echo "  # Generate self-signed certificate:"
echo "  podman run --rm -v ./test-certs:/data/state/certificates localhost/podserve-harmony-certificates:${TAG} python3 -m podserve certificates --mode init"