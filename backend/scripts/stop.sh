#!/bin/bash

# Stop Script for Identity API Backend
# Stops FastAPI application and Supabase local instance

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Identity API Backend - Stop${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Navigate to backend directory if not already there
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

echo -e "${GREEN}[1/2] Stopping FastAPI application...${NC}"
# Stop Docker Compose services
if docker compose ps -q | grep -q .; then
    docker compose down
    echo -e "${GREEN}FastAPI service stopped${NC}"
else
    echo -e "${YELLOW}FastAPI service was not running${NC}"
fi
echo ""

echo -e "${GREEN}[2/2] Stopping Supabase...${NC}"
# Stop Supabase
if supabase status &> /dev/null; then
    supabase stop
    echo -e "${GREEN}Supabase services stopped${NC}"
else
    echo -e "${YELLOW}Supabase was not running${NC}"
fi
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}All Services Stopped${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} Database data is preserved"
echo -e "To completely clean volumes: docker compose down -v"
echo ""

