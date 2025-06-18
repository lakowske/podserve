#!/bin/bash
set -e

# Build script for PodServe Docker images

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="${REGISTRY:-localhost}"
TAG="${TAG:-latest}"
PUSH="${PUSH:-false}"
BUILD_ARGS=""

# Function to print colored output
log() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Function to build an image
build_image() {
    local name=$1
    local dockerfile=$2
    local context=$3
    local tag="${REGISTRY}/podserve-${name}:${TAG}"
    
    log "Building $name image..."
    log "  Dockerfile: $dockerfile"
    log "  Context: $context"
    log "  Tag: $tag"
    
    if podman build $BUILD_ARGS -t "$tag" -f "$dockerfile" "$context"; then
        log "Successfully built $tag"
        
        # Tag as latest if not already
        if [[ "$TAG" != "latest" ]]; then
            podman tag "$tag" "${REGISTRY}/podserve-${name}:latest"
            log "Tagged as ${REGISTRY}/podserve-${name}:latest"
        fi
        
        # Push if requested
        if [[ "$PUSH" == "true" ]]; then
            log "Pushing $tag..."
            if podman push "$tag"; then
                log "Successfully pushed $tag"
            else
                error "Failed to push $tag"
                return 1
            fi
        fi
    else
        error "Failed to build $name image"
        return 1
    fi
}

# Function to discover available images
discover_images() {
    local images=()
    for dir in */; do
        dir=${dir%/}  # Remove trailing slash
        if [[ -f "${dir}/Dockerfile" ]]; then
            images+=("$dir")
        fi
    done
    echo "${images[@]}"
}

# Function to check image dependencies
get_image_dependencies() {
    local dockerfile=$1
    local deps=()
    
    # Look for FROM statements that reference our base image
    if grep -q "FROM localhost/podserve-base" "$dockerfile" 2>/dev/null; then
        deps+=("base")
    fi
    
    echo "${deps[@]}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --push)
            PUSH="true"
            shift
            ;;
        --no-cache)
            BUILD_ARGS="$BUILD_ARGS --no-cache"
            shift
            ;;
        --platform)
            BUILD_ARGS="$BUILD_ARGS --platform $2"
            shift 2
            ;;
        -h|--help)
            # Change to script directory to discover images
            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
            cd "$SCRIPT_DIR"
            
            echo "Usage: $0 [OPTIONS] [IMAGE_NAMES...]"
            echo ""
            echo "Build PodServe Docker images"
            echo ""
            echo "Options:"
            echo "  --registry REGISTRY  Docker registry (default: localhost)"
            echo "  --tag TAG           Image tag (default: latest)"
            echo "  --push              Push images after building"
            echo "  --no-cache          Build without cache"
            echo "  --platform PLATFORM Platform to build for (e.g., linux/amd64)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Available images:"
            
            # Dynamically list available images
            available_images=($(discover_images))
            for img in "${available_images[@]}"; do
                # Try to extract description from Dockerfile LABEL
                desc=$(grep -m1 "^LABEL description=" "${img}/Dockerfile" 2>/dev/null | sed 's/LABEL description="//' | sed 's/"$//')
                if [[ -n "$desc" ]]; then
                    printf "  %-10s %s\n" "$img" "$desc"
                else
                    printf "  %-10s\n" "$img"
                fi
            done
            
            echo "  all      Build all images (default)"
            echo ""
            echo "Examples:"
            echo "  $0                           # Build all images"
            echo "  $0 base certbot              # Build specific images"
            echo "  $0 --push --tag v1.0.0       # Build and push with tag"
            echo "  $0 --registry myregistry.com # Build with custom registry"
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

# Determine which images to build
if [[ $# -eq 0 ]]; then
    IMAGES="all"
else
    IMAGES="$@"
fi

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log "Starting PodServe image builds..."
log "Registry: $REGISTRY"
log "Tag: $TAG"
log "Push: $PUSH"

# Track failures
FAILED=()

# Discover available images
available_images=($(discover_images))

# Determine which images to build
if [[ "$IMAGES" == "all" ]]; then
    images_to_build=("${available_images[@]}")
else
    images_to_build=($IMAGES)
fi

# Build a map of built images to avoid rebuilding
declare -A built_images

# Function to build image with dependencies
build_with_dependencies() {
    local name=$1
    
    # Skip if already built
    if [[ -n "${built_images[$name]}" ]]; then
        return 0
    fi
    
    # Check if this image exists in our directories
    if [[ ! -f "${name}/Dockerfile" ]]; then
        error "No Dockerfile found for image: $name"
        return 1
    fi
    
    # Get dependencies
    local deps=($(get_image_dependencies "${name}/Dockerfile"))
    
    # Build dependencies first
    for dep in "${deps[@]}"; do
        if [[ -z "${built_images[$dep]}" ]]; then
            if ! podman image inspect "${REGISTRY}/podserve-${dep}:${TAG}" >/dev/null 2>&1; then
                warning "Dependency ${dep} not found, building it first..."
                if ! build_with_dependencies "$dep"; then
                    error "Failed to build required dependency: $dep"
                    return 1
                fi
            fi
        fi
    done
    
    # Build the image
    if build_image "$name" "${name}/Dockerfile" "."; then
        built_images[$name]=1
        return 0
    else
        FAILED+=("$name")
        return 1
    fi
}

# Build requested images
for img in "${images_to_build[@]}"; do
    build_with_dependencies "$img"
done

# Summary
echo ""
log "Build Summary:"
log "=============="

if [[ ${#FAILED[@]} -eq 0 ]]; then
    log "All images built successfully!"
    
    # List built images
    echo ""
    log "Built images:"
    podman images "${REGISTRY}/podserve-*" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
else
    error "Failed to build: ${FAILED[*]}"
    exit 1
fi

# Provide next steps
echo ""
log "Next steps:"
echo "  1. Test the images locally:"
echo "     podman run --rm ${REGISTRY}/podserve-certbot:${TAG} check"
echo ""
echo "  2. Use in a pod with podman play:"
echo "     Update podserve-pod.yaml with these image names"
echo ""
if [[ "$PUSH" != "true" ]]; then
    echo "  3. Push images when ready:"
    echo "     $0 --push --tag ${TAG}"
fi