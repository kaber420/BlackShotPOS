#!/bin/bash
# Script to build BlackShotPOS Docker images with multi-architecture support
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
DOCKER_USER="${DOCKER_USER:-blackshot}"
BUILD_TARGET="local" # Default option

# Parse command line argument (friendly flags)
if [ -n "$1" ]; then
    case "$1" in
        "--arm64")
            BUILD_TARGET="arm64"
            ;;
        "--amd64")
            BUILD_TARGET="amd64"
            ;;
        "--multi")
            BUILD_TARGET="multi"
            ;;
        "--local")
            BUILD_TARGET="local"
            ;;
        "-h"|"--help")
            echo -e "${BLUE}BlackShotPOS Docker Builder Options:${NC}"
            echo -e "  ${GREEN}bash scripts/docker-build.sh${NC}          Builds for local host architecture (Default)"
            echo -e "  ${GREEN}bash scripts/docker-build.sh --arm64${NC}  Builds for ARM64 (SBC / Raspberry Pi)"
            echo -e "  ${GREEN}bash scripts/docker-build.sh --amd64${NC}  Builds for AMD64 (Standard PC/Laptop)"
            echo -e "  ${GREEN}bash scripts/docker-build.sh --multi${NC}  Builds both AMD64 and ARM64 and pushes them"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Invalid argument '$1'.${NC}"
            echo -e "Available options: --local, --arm64, --amd64, --multi, --help"
            exit 1
            ;;
    esac
fi

echo -e "${BLUE}==> Validating Build Target: ${YELLOW}${BUILD_TARGET}${NC}"

# Check for Docker Buildx capability
HAS_BUILDX=true
if ! docker buildx version &> /dev/null; then
    HAS_BUILDX=false
    echo -e "${YELLOW}Warning: docker buildx is not installed or enabled in your Docker daemon.${NC}"
    if [ "$BUILD_TARGET" != "local" ]; then
        echo -e "${RED}Error: Build target '${BUILD_TARGET}' requires Docker Buildx. Aborting.${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Falling back to standard 'docker build' for local architecture.${NC}"
fi

# Ensure multi-architecture builder instance exists and is active (only if buildx is available)
BUILDER_NAME="blackshot_builder"
if [ "$HAS_BUILDX" = true ]; then
    if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
        echo -e "${YELLOW}==> Creating new Docker Buildx builder instance: ${BLUE}${BUILDER_NAME}${NC}"
        docker buildx create --name "$BUILDER_NAME" --driver docker-container --use
        docker buildx inspect --bootstrap
    else
        echo -e "${BLUE}==> Using existing builder instance: ${GREEN}${BUILDER_NAME}${NC}"
        docker buildx use "$BUILDER_NAME"
    fi
fi

# 1. Compile SvelteKit Frontend Static Assets locally
echo -e "\n${BLUE}==> Building Frontend Static Assets...${NC}"
if ! command -v pnpm &> /dev/null; then
    echo -e "${RED}Error: pnpm could not be found. Please install it first.${NC}"
    exit 1
fi

# Ensure .env exists in frontend for SvelteKit build
if [ -f .env ]; then
    cp .env bs_frontend/.env
fi

cd bs_frontend
pnpm build
cd ..

# 2. Configure Platforms and Build Actions (if using buildx)
PLATFORM=""
ACTION=""

if [ "$HAS_BUILDX" = true ]; then
    case "$BUILD_TARGET" in
        "multi")
            PLATFORM="linux/amd64,linux/arm64"
            ACTION="--push"
            echo -e "\n${YELLOW}==> MODE: Multi-Architecture Build & Push (${PLATFORM})${NC}"
            echo -e "Make sure you are logged in to your registry: ${BLUE}docker login${NC}"
            ;;
        "arm64")
            PLATFORM="linux/arm64"
            ACTION="--load"
            echo -e "\n${YELLOW}==> MODE: Single-Arch ARM64 Build & Local Load (${PLATFORM})${NC}"
            ;;
        "amd64")
            PLATFORM="linux/amd64"
            ACTION="--load"
            echo -e "\n${YELLOW}==> MODE: Single-Arch AMD64 Build & Local Load (${PLATFORM})${NC}"
            ;;
        "local")
            PLATFORM=""
            ACTION="--load"
            echo -e "\n${YELLOW}==> MODE: Default Host Architecture Build & Local Load${NC}"
            ;;
    esac
else
    echo -e "\n${YELLOW}==> MODE: Standard Local Build (No Buildx)${NC}"
fi

# 3. Compile Backend Images
echo -e "\n${BLUE}==> Building Backend and Sync Agent Image (${DOCKER_USER}/pos-backend:latest)...${NC}"
if [ "$HAS_BUILDX" = true ]; then
    if [ -n "$PLATFORM" ]; then
        docker buildx build \
            --platform "$PLATFORM" \
            -f docker/backend/Dockerfile \
            -t "${DOCKER_USER}/pos-backend:latest" \
            $ACTION \
            .
    else
        docker buildx build \
            -f docker/backend/Dockerfile \
            -t "${DOCKER_USER}/pos-backend:latest" \
            $ACTION \
            .
    fi
else
    docker build \
        -f docker/backend/Dockerfile \
        -t "${DOCKER_USER}/pos-backend:latest" \
        .
fi

# 4. Compile Frontend Images
echo -e "\n${BLUE}==> Building Frontend Image (${DOCKER_USER}/pos-frontend:latest)...${NC}"
if [ "$HAS_BUILDX" = true ]; then
    if [ -n "$PLATFORM" ]; then
        docker buildx build \
            --platform "$PLATFORM" \
            -f docker/frontend/Dockerfile \
            -t "${DOCKER_USER}/pos-frontend:latest" \
            $ACTION \
            bs_frontend
    else
        docker buildx build \
            -f docker/frontend/Dockerfile \
            -t "${DOCKER_USER}/pos-frontend:latest" \
            $ACTION \
            bs_frontend
    fi
else
    docker build \
        -f docker/frontend/Dockerfile \
        -t "${DOCKER_USER}/pos-frontend:latest" \
        bs_frontend
fi

echo -e "\n${GREEN}==> Build Process Complete!${NC}"
if [ "$HAS_BUILDX" = true ] && [ "$BUILD_TARGET" = "multi" ]; then
    echo -e "Images have been pushed to: ${BLUE}${DOCKER_USER}/pos-backend:latest${NC} and ${BLUE}${DOCKER_USER}/pos-frontend:latest${NC}"
else
    echo -e "Images have been successfully loaded into your local Docker daemon."
    echo -e "You can run them using:"
    echo -e "  ${BLUE}docker compose -f docker/docker-compose.yml up -d${NC}"
fi
