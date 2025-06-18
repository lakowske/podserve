#!/bin/bash
# Build script for developer-friendly containers
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

echo "Building with UID=${USER_UID}, GID=${USER_GID}, USER=${USERNAME}"

# Service to build
SERVICE=${1:-all}

# Function to build a service
build_service() {
    local service_name=$1
    local dockerfile=${2:-Dockerfile.developer}
    
    echo "Building ${service_name} service..."
    
    if [ -d "${service_name}" ]; then
        pushd "${service_name}" > /dev/null
        
        # Use developer-friendly Dockerfile if it exists
        if [ -f "${dockerfile}" ]; then
            podman build "${BUILD_ARGS[@]}" -f "${dockerfile}" -t "localhost/podserve-${service_name}:${TAG}" .
        else
            echo "Warning: ${dockerfile} not found, falling back to regular Dockerfile"
            podman build "${BUILD_ARGS[@]}" -t "localhost/podserve-${service_name}:${TAG}" .
        fi
        
        popd > /dev/null
        echo "✓ Built podserve-${service_name}:${TAG}"
    else
        echo "Error: Directory ${service_name} not found"
        exit 1
    fi
}

# Build base image first
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "base" ]; then
    echo "Building base image..."
    build_service "base" "Dockerfile.developer"
fi

# Build other services
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "apache" ]; then
    build_service "apache" "Dockerfile.developer"
fi

if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "mail" ]; then
    build_service "mail" "Dockerfile.developer"  
fi

if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "dns" ]; then
    build_service "dns" "Dockerfile.developer"
fi

if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "certbot" ]; then
    build_service "certbot" "Dockerfile.developer"
fi

echo ""
echo "Build complete! Container images:"
podman images | grep "localhost/podserve-" | grep "${TAG}"

echo ""
echo "To deploy with development volumes:"
echo "  podman play kube dev.yaml"
echo ""
echo "To test a service:"
echo "  podman run --rm -e LOG_LEVEL=DEBUG localhost/podserve-${SERVICE}:${TAG}"