# Backend Setup Guide

Complete setup guide for the Identity and Profile Management API backend.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Database Setup](#database-setup)
4. [Running Tests](#running-tests)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

1. **Docker Desktop** (20.10 or higher)
   - Download: https://www.docker.com/products/docker-desktop
   - Verify: `docker --version` and `docker compose version`

2. **Supabase CLI**
   ```bash
   # macOS
   brew install supabase/tap/supabase
   
   # Windows (scoop)
   scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
   scoop install supabase
   
   # Linux
   curl -fsSL https://raw.githubusercontent.com/supabase/cli/main/install.sh | sh
   ```
   - Verify: `supabase --version`

3. **Git**
   - Verify: `git --version`

4. **Python 3.12+** (optional, for local development without Docker)
   - Verify: `python --version`

### System Requirements

- **RAM:** 4GB minimum, 8GB recommended
- **Disk Space:** 5GB for Docker images and databases
- **OS:** macOS, Linux, or Windows with WSL2

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd thesis/backend
```

### Step 2: Choose Setup Method

You have two options:

#### Option A: Automated Setup (Recommended)

Use the provided management scripts for easy setup:

```bash
# Copy environment template
cp env.local.template .env

# Make scripts executable
chmod +x scripts/*.sh

# Start everything
./scripts/start.sh
```

The script will:
1. Check all prerequisites
2. Start Supabase services
3. Apply database migrations
4. Load seed data
5. Start FastAPI application
6. Display service URLs

**Access your services:**
- API Documentation: http://localhost:8000/docs
- Supabase Studio: http://127.0.0.1:54323
- API: http://localhost:8000

#### Option B: Manual Setup

For more control over the setup process:

1. **Copy environment file:**
   ```bash
   cp env.local.template .env
   ```

2. **Start Supabase:**
   ```bash
   supabase start
   ```
   
   Note the output - you'll see URLs and keys.

3. **Verify Supabase is running:**
   ```bash
   supabase status
   ```

4. **Update environment variables** (if needed):
   
   The `.env` file should work out of the box with local Supabase defaults. If you need to customize:
   
   ```bash
   # Edit .env and update these values from 'supabase status' output:
   SUPABASE_URL=http://127.0.0.1:54321
   SUPABASE_ANON_KEY=<from supabase status>
   SUPABASE_SERVICE_KEY=<from supabase status>
   DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
   ```

5. **Start FastAPI application:**
   ```bash
   docker compose up -d
   ```

6. **Apply migrations and seed data:**
   ```bash
   supabase db reset
   ```

7. **Verify installation:**
   ```bash
   curl http://localhost:8000/health
   ```

### Step 3: Verify Setup

Test that everything is working:

1. **Health Check:**
   ```bash
   curl http://localhost:8000/health/detailed
   ```
   
   You should see all components reporting as "healthy".

2. **Database Test:**
   ```bash
   curl http://localhost:8000/api/v1/database/test
   ```
   
   You should see sample profiles from seed data.

3. **Interactive API Docs:**
   
   Open http://localhost:8000/docs in your browser. You should see the Swagger UI.

4. **Supabase Studio:**
   
   Open http://127.0.0.1:54323 to access Supabase Studio (database UI).

## Database Setup

### Understanding the Database Structure

The system uses two core tables:

1. **base_profiles** - Core user profiles
   - Supports 3 account types: verified, unverified, pseudonymous
   - Stores basic contact info and preferences

2. **identity_names** - Multilingual name storage
   - JSONB field for flexible name representation
   - Supports multiple naming conventions (Western, Chinese, mononym, etc.)

### Migrations

Migrations are stored in `supabase/migrations/` as SQL files.

#### View migrations:
```bash
supabase migration list
```

#### Apply all migrations (reset database):
```bash
supabase db reset
```

This will:
1. Drop all existing data
2. Apply all migrations in order
3. Load seed data from `supabase/seed.sql`

#### Create a new migration:
```bash
# Make changes in Supabase Studio
# Then generate migration from changes
supabase db diff -f description_of_changes
```

### Seed Data

The system comes with sample data for testing:

- 5 sample profiles with different account types
- Multiple naming conventions (Western, Chinese, mononym, etc.)
- Examples of deprecated names (deadnames)

Seed data is automatically loaded when you run `supabase db reset`.

### Direct Database Access

Connect directly to PostgreSQL:

```bash
# Using psql
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Using a GUI client (DBeaver, pgAdmin, etc.)
Host: 127.0.0.1
Port: 54322
Database: postgres
Username: postgres
Password: postgres
```

## Running Tests

### Prerequisites for Testing

Ensure services are running:
```bash
./scripts/status.sh
```

### Run All Tests

```bash
docker compose exec api pytest
```

### Run with Coverage

```bash
docker compose exec api pytest --cov=src --cov-report=term-missing --cov-report=html
```

View HTML coverage report: `open htmlcov/index.html`

### Run Specific Test Categories

```bash
# Unit tests only
docker compose exec api pytest tests/unit/

# Integration tests only
docker compose exec api pytest tests/integration/

# Specific test file
docker compose exec api pytest tests/unit/test_models.py

# Specific test function
docker compose exec api pytest tests/unit/test_models.py::test_create_base_profile

# Tests matching a pattern
docker compose exec api pytest -k "profile"
```

### Test Output Options

```bash
# Verbose output
docker compose exec api pytest -v

# Very verbose (shows test names)
docker compose exec api pytest -vv

# Show print statements
docker compose exec api pytest -s

# Stop on first failure
docker compose exec api pytest -x

# Run last failed tests
docker compose exec api pytest --lf
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error:** `port 54322 is already in use`

**Solution:**
```bash
# Find what's using the port
lsof -i :54322

# Stop existing Supabase instance
supabase stop

# Or force kill the process
kill -9 <PID>
```

#### 2. Docker Not Running

**Error:** `Cannot connect to the Docker daemon`

**Solution:**
- Start Docker Desktop
- Verify: `docker ps`

#### 3. Database Connection Failed

**Error:** `Database connection failed`

**Solution:**
```bash
# Check Supabase status
supabase status

# Restart Supabase
supabase stop
supabase start

# Verify database is accessible
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c "SELECT 1"
```

#### 4. Migrations Not Applied

**Error:** `Table 'base_profiles' doesn't exist`

**Solution:**
```bash
# Reset database (applies all migrations)
supabase db reset

# Or apply migrations manually
supabase db push
```

#### 5. FastAPI Not Starting

**Error:** `FastAPI container exits immediately`

**Solution:**
```bash
# View logs
docker compose logs api

# Check environment variables
docker compose exec api env | grep DATABASE_URL

# Rebuild container
docker compose down
docker compose up --build
```

#### 6. Tests Failing

**Error:** Various test failures

**Solution:**
```bash
# Ensure fresh database
./scripts/reset.sh

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Run tests with verbose output
docker compose exec api pytest -vv
```

### Getting Help

If you're still stuck:

1. **Check service status:**
   ```bash
   ./scripts/status.sh
   ```

2. **View recent logs:**
   ```bash
   docker compose logs --tail=50 api
   ```

3. **Verify environment:**
   ```bash
   cat .env
   supabase status
   docker ps
   ```

4. **Test database connectivity:**
   ```bash
   curl http://localhost:8000/health/detailed
   ```

5. **Reset everything:**
   ```bash
   ./scripts/stop.sh
   docker compose down -v
   supabase stop
   # Then start fresh
   ./scripts/start.sh
   ```

## Next Steps

After successful setup:

1. **Explore the API:** http://localhost:8000/docs
2. **Browse database:** http://127.0.0.1:54323
3. **Run tests:** `docker compose exec api pytest`
4. **Read architecture docs:** `../architecture/`

## Additional Resources

- **Main README:** `../README.md`
- **Backend README:** `README.md`
- **Architecture Documentation:** `../architecture/`
- **Supabase Docs:** https://supabase.com/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com

