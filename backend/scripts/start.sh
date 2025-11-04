#!/bin/bash

# Start Script for Identity API Backend
# Starts Supabase local instance and FastAPI application

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Identity API Backend - Start${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo -e "${RED}Error: Supabase CLI is not installed${NC}"
    echo "Install with: brew install supabase/tap/supabase"
    echo "Or visit: https://supabase.com/docs/guides/cli"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Navigate to backend directory if not already there
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

echo -e "${GREEN}[1/4] Starting Supabase...${NC}"
# Start Supabase (will skip if already running)
if supabase status &> /dev/null; then
    echo -e "${YELLOW}Supabase is already running${NC}"
else
    supabase start
fi
echo ""

echo -e "${GREEN}[2/4] Waiting for Supabase to be ready...${NC}"
# Wait a moment for services to fully initialize
sleep 2
echo ""

echo -e "${GREEN}[3/4] Starting FastAPI application...${NC}"
# Start Docker Compose services
docker compose up -d
echo ""

echo -e "${GREEN}[4/4] Verifying services...${NC}"
sleep 3

# Get Supabase status
echo ""
echo -e "${BLUE}Supabase Services:${NC}"
supabase status | grep -E "(API URL|DB URL|Studio URL|Inbucket URL)"
echo ""

# Check if FastAPI is running
if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}FastAPI service is running${NC}"
else
    echo -e "${YELLOW}FastAPI service status unknown${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Services Started Successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Access the services at:${NC}"
echo -e "  ${GREEN}FastAPI Application:${NC}  http://localhost:8000"
echo -e "  ${GREEN}API Documentation:${NC}    http://localhost:8000/docs"
echo -e "  ${GREEN}Supabase Studio:${NC}      http://127.0.0.1:54323"
echo -e "  ${GREEN}Database Direct:${NC}      postgresql://postgres:postgres@127.0.0.1:54322/postgres"
echo ""
echo -e "${YELLOW}To view logs:${NC}      ./scripts/status.sh"
echo -e "${YELLOW}To stop services:${NC}  ./scripts/stop.sh"
echo -e "${YELLOW}To reset database:${NC} ./scripts/reset.sh"
echo ""

