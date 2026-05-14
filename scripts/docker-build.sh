#!/bin/bash
# Script to build BlackShotPOS Docker images
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==> Building Frontend Static Assets...${NC}"
if ! command -v pnpm &> /dev/null
then
    echo "Error: pnpm could not be found. Please install it first."
    exit 1
fi

# Ensure .env exists in frontend for SvelteKit build
cp .env bs_frontend/.env

cd bs_frontend
pnpm build
cd ..

echo -e "\n${BLUE}==> Building Docker Images...${NC}"
# Use the docker-compose file in the docker/ directory
# Setting DOCKER_USER variable if you want to override it
# Example: DOCKER_USER=myuser bash scripts/docker-build.sh
docker compose -f docker/docker-compose.yml build

echo -e "\n${GREEN}==> Build Complete!${NC}"
echo -e "You can now push your images to Docker Hub using:"
echo -e "  ${BLUE}docker-compose -f docker/docker-compose.yml push${NC}"
echo -e "Or run them locally with:"
echo -e "  ${BLUE}docker-compose -f docker/docker-compose.yml up -d${NC}"
