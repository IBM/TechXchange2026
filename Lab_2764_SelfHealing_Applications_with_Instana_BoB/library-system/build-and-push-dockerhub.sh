#!/bin/bash

# Script to build Docker images locally and push to Docker Hub
# Prerequisites:
#   - Docker installed and running
#   - Logged in to Docker Hub: docker login
#   - Docker Buildx enabled (included with Docker Desktop)

set -e

# Configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-dockerhub-username}"
IMAGE_TAG="${IMAGE_TAG:-v1.0.4}"
# Target platform — OCP/K8s clusters typically run linux/amd64.
# Override with: BUILD_PLATFORM=linux/arm64 or linux/amd64,linux/arm64
BUILD_PLATFORM="${BUILD_PLATFORM:-linux/amd64}"

echo "=========================================="
echo "Docker Hub Build and Push Script"
echo "=========================================="
echo ""

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon is not running"
    echo "Please start Docker"
    exit 1
fi

# Check if logged in to Docker Hub
if ! docker info | grep -q "Username"; then
    echo "⚠️  Warning: You may not be logged in to Docker Hub"
    echo "Please run: docker login"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Prompt for Docker Hub username if not set
if [ "$DOCKER_USERNAME" = "your-dockerhub-username" ]; then
    echo "Docker Hub username not set."
    read -p "Enter your Docker Hub username: " DOCKER_USERNAME
    if [ -z "$DOCKER_USERNAME" ]; then
        echo "❌ Error: Docker Hub username is required"
        exit 1
    fi
fi

# Ensure a buildx builder that supports multi-platform builds is active
if ! docker buildx inspect multiplatform-builder &> /dev/null; then
    echo "Creating buildx builder for multi-platform support..."
    docker buildx create --name multiplatform-builder --use
else
    docker buildx use multiplatform-builder
fi

echo "✓ Docker is running"
echo "✓ Docker Hub username: $DOCKER_USERNAME"
echo "✓ Image tag: $IMAGE_TAG"
echo "✓ Build platform: $BUILD_PLATFORM"
echo ""

# Confirm before proceeding
echo "This script will build and push the following images:"
echo "  - $DOCKER_USERNAME/library-books-api:$IMAGE_TAG"
echo "  - $DOCKER_USERNAME/library-users-api:$IMAGE_TAG"
echo "  - $DOCKER_USERNAME/library-web-ui:$IMAGE_TAG"
echo "  - $DOCKER_USERNAME/library-load-generator:$IMAGE_TAG"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "=========================================="
echo "Building and Pushing Images"
echo "=========================================="
echo ""

# Array of services
services=("books-api" "users-api" "web-ui" "load-generator")

# Build and push each service
for service in "${services[@]}"; do
    echo "=========================================="
    echo "Processing $service"
    echo "=========================================="
    
    # Set image name
    IMAGE_NAME="$DOCKER_USERNAME/library-$service:$IMAGE_TAG"
    
    echo "Building and pushing $IMAGE_NAME (platform: $BUILD_PLATFORM)..."
    # --push builds and pushes in one step; required for multi-platform manifests
    if docker buildx build \
        --platform "$BUILD_PLATFORM" \
        --tag "$IMAGE_NAME" \
        --push \
        ./$service; then
        echo "✓ Build and push successful"
    else
        echo "❌ Failed to build/push $IMAGE_NAME"
        exit 1
    fi
    
    echo ""
done

echo "=========================================="
echo "✅ All Images Built and Pushed!"
echo "=========================================="
echo ""
echo "Images built for platform '$BUILD_PLATFORM' and pushed to Docker Hub:"
for service in "${services[@]}"; do
    echo "  ✓ $DOCKER_USERNAME/library-$service:$IMAGE_TAG"
done
echo ""
echo "To pull these images:"
for service in "${services[@]}"; do
    echo "  docker pull --platform $BUILD_PLATFORM $DOCKER_USERNAME/library-$service:$IMAGE_TAG"
done
echo ""
echo "To use in Kubernetes/OpenShift, update image references to:"
for service in "${services[@]}"; do
    echo "  image: $DOCKER_USERNAME/library-$service:$IMAGE_TAG"
done
echo ""

# Made with Bob