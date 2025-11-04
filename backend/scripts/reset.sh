#!/bin/bash

# Reset Script for Identity API Backend
# Resets database (applies migrations and seeds), then restarts services

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Identity API Backend - Database Reset${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Navigate to backend directory if not already there
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

# Confirmation prompt
echo -e "${YELLOW}WARNING: This will reset the database and reload seed data${NC}"
echo -e "${YELLOW}All existing data will be lost!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${RED}Database reset cancelled${NC}"
    exit 0
fi

echo -e "${GREEN}[1/4] Stopping services...${NC}"
./scripts/stop.sh > /dev/null 2>&1 || true
echo ""

echo -e "${GREEN}[2/4] Starting Supabase...${NC}"
supabase start
echo ""

echo -e "${GREEN}[3/4] Resetting database (applying migrations and seeds)...${NC}"
supabase db reset
echo ""

echo -e "${GREEN}[4/4] Restarting FastAPI application...${NC}"
docker compose up -d
sleep 2
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Database Reset Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}What happened:${NC}"
echo "  1. All tables dropped"
echo "  2. Migrations applied (schema recreated)"
echo "  3. Seed data loaded"
echo "  4. Services restarted"
echo ""
echo -e "${GREEN}Services are now running with fresh seed data${NC}"
echo -e "Access FastAPI: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "Access Supabase Studio: ${BLUE}http://127.0.0.1:54323${NC}"
echo ""

