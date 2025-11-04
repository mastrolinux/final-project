#!/bin/bash

# Status Script for Identity API Backend
# Shows status of all services and recent logs

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Identity API Backend - Status${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Navigate to backend directory if not already there
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

# Check Supabase status
echo -e "${BLUE}Supabase Services:${NC}"
if supabase status &> /dev/null; then
    supabase status
else
    echo -e "${RED}Supabase is not running${NC}"
    echo "Start with: ./scripts/start.sh"
fi
echo ""

# Check Docker Compose status
echo -e "${BLUE}FastAPI Service:${NC}"
if docker compose ps | grep -q "Up"; then
    docker compose ps
else
    echo -e "${RED}FastAPI service is not running${NC}"
    echo "Start with: ./scripts/start.sh"
fi
echo ""

# Show recent logs
echo -e "${BLUE}Recent FastAPI Logs (last 20 lines):${NC}"
if docker compose ps -q | grep -q .; then
    docker compose logs --tail=20 api || echo -e "${YELLOW}No logs available${NC}"
else
    echo -e "${YELLOW}Service not running - no logs available${NC}"
fi
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Service URLs:${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  ${GREEN}FastAPI Application:${NC}  http://localhost:8000"
echo -e "  ${GREEN}API Documentation:${NC}    http://localhost:8000/docs"
echo -e "  ${GREEN}Health Check:${NC}         http://localhost:8000/health"
echo -e "  ${GREEN}Detailed Health:${NC}      http://localhost:8000/health/detailed"
echo -e "  ${GREEN}Database Test:${NC}        http://localhost:8000/api/v1/database/test"
echo -e "  ${GREEN}Supabase Studio:${NC}      http://127.0.0.1:54323"
echo -e "  ${GREEN}Inbucket (Email):${NC}     http://127.0.0.1:54324"
echo ""
echo -e "${BLUE}Database Connection:${NC}"
echo -e "  postgresql://postgres:postgres@127.0.0.1:54322/postgres"
echo ""
echo -e "${YELLOW}Commands:${NC}"
echo -e "  View live logs:    docker compose logs -f"
echo -e "  Restart services:  ./scripts/stop.sh && ./scripts/start.sh"
echo -e "  Reset database:    ./scripts/reset.sh"
echo ""

