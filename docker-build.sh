#!/bin/bash

# Multi-architecture Docker build script
# Usage: ./docker-build.sh <image-name> [push]
# Example: ./docker-build.sh myregistry/ilovepdf:latest push

IMAGE_NAME=${1:-"ilovepdf:latest"}
PUSH_FLAG=${2:-""}

# Create buildx builder if it doesn't exist
docker buildx create --name multiarch --use 2>/dev/null || docker buildx use multiarch

# Build for both architectures
if [ "$PUSH_FLAG" == "push" ]; then
    echo "Building and pushing multi-arch image: $IMAGE_NAME"
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -t "$IMAGE_NAME" \
        --push \
        .
else
    echo "Building multi-arch image locally: $IMAGE_NAME"
    echo "Note: For local build, only your native arch will be loaded"
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -t "$IMAGE_NAME" \
        --load \
        .
fi
