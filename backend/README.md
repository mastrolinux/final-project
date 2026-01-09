# Identity and Profile Management API - Backend

A sophisticated identity and profile management system designed to handle complex digital identity across cultural, contextual, and regulatory boundaries. Built as an academic thesis project prioritizing production-readiness and GDPR compliance.

## Features

- Multi-context identity management (professional, social, legal contexts)
- Cultural neutrality (no assumptions about naming conventions)
- Guardian-managed identities for minors
- GDPR Article 15-22 compliance (privacy-by-design)
- OAuth 2.0 authorization server with scope-based access control

## Technology Stack

- **Language:** Python 3.12
- **Framework:** FastAPI
- **Database:** PostgreSQL 15+ (Supabase)
- **ORM:** SQLAlchemy
- **Migrations:** Supabase CLI
- **Development:** Docker & Docker Compose

## Prerequisites

- Docker (20.10 or higher)
- Docker Compose (2.0 or higher)
- Supabase CLI
- Git

## Quick Start

### Option 1: Using Management Scripts (Recommended)

The easiest way to get started is using the provided management scripts:

```bash
# 1. Clone the repository
git clone <repository-url>
cd thesis/backend

# 2. Copy environment template
cp env.local.template .env

# 3. Start all services (Supabase + FastAPI)
chmod +x scripts/*.sh
./scripts/start.sh
```

That's it! The start script will:
- Check prerequisites (Docker, Supabase CLI)
- Start Supabase services
- Apply database migrations and seed data
- Start FastAPI application
- Display all service URLs

**Management Commands:**
- `./scripts/start.sh` - Start all services
- `./scripts/stop.sh` - Stop all services
- `./scripts/reset.sh` - Reset database (reapply migrations + seeds)
- `./scripts/status.sh` - Check service status and view logs

### Option 2: Manual Setup

If you prefer manual control:

#### 1. Install Prerequisites

```bash
# macOS
brew install supabase/tap/supabase

# Other platforms: https://supabase.com/docs/guides/cli
```

#### 2. Start Supabase

```bash
supabase start
```

#### 3. Configure Environment

```bash
cp env.local.template .env
# Update with values from 'supabase status' output
```

#### 4. Start FastAPI

```bash
docker compose up -d
```

#### 5. Apply Migrations

```bash
supabase db reset
```

### Verify Installation

Visit http://localhost:8000/docs to access the interactive API documentation.

**Available Services:**
- **API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Detailed Health:** http://localhost:8000/health/detailed
- **Database Test:** http://localhost:8000/api/v1/database/test
- **Supabase Studio:** http://127.0.0.1:54323
- **Email Testing:** http://127.0.0.1:54324
- **Database:** postgresql://postgres:postgres@127.0.0.1:54322/postgres

## Development Workflow

### Using Management Scripts

The backend includes convenient management scripts for common operations:

#### Start Services
```bash
./scripts/start.sh
```
Starts Supabase and FastAPI, displays service URLs.

#### Check Status
```bash
./scripts/status.sh
```
Shows service status, recent logs, and available URLs.

#### Reset Database
```bash
./scripts/reset.sh
```
Resets database (applies migrations and seeds), useful for testing.

#### Stop Services
```bash
./scripts/stop.sh
```
Gracefully stops all services, preserves data.

### Manual Service Management

**Supabase:**
```bash
# Start Supabase
supabase start

# Check status
supabase status

# Stop Supabase
supabase stop

# Check Supabase status and get connection details
supabase status

# Reset database (CAUTION: deletes all data)
supabase db reset
```

**FastAPI Application:**
```bash
# Start the API
docker compose up

# Start in detached mode
docker compose up -d

# Stop the API
docker compose down
```

### Viewing Logs

```bash
# View all logs
docker compose logs

# Follow logs (live tail)
docker compose logs -f

# View API logs only
docker compose logs -f api
```

### Running Commands Inside Container

```bash
# Access API container shell
docker compose exec api bash

# Run tests
docker compose exec api pytest

# Run tests with coverage
docker compose exec api pytest --cov=src --cov-report=term-missing
```

### Database Management

```bash
# Generate migration from schema changes
supabase db diff -f migration_name

# Apply migrations locally (resets database)
supabase db reset

# Deploy migrations to remote Supabase
supabase db push

# Access PostgreSQL shell (local Supabase)
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Create database backup (local Supabase)
pg_dump postgresql://postgres:postgres@127.0.0.1:54322/postgres > backup.sql
```

### Code Quality

```bash
# Type checking
docker compose exec api mypy src/

# Linting
docker compose exec api ruff check src/

# Format code
docker compose exec api black src/

# Security scanning
docker compose exec api bandit -r src/
```

## Project Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI app initialization
│   ├── core/
│   │   ├── config.py        # Configuration management
│   │   └── database.py      # Database connection
│   └── api/
│       └── v1/
│           └── router.py    # API v1 router
├── tests/                   # Test files (to be added)
├── supabase/                # Supabase configuration
│   ├── migrations/          # Database migrations (SQL)
│   └── config.toml          # Supabase settings
├── docs/                    # Architecture documentation
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Docker services configuration
├── requirements.txt         # Python dependencies
├── env.local.template      # Local development environment template
├── env.production.template # Production environment template
└── README.md               # This file
```

## Next Steps

1. **Create your first model** in `src/models/`

2. **Create your first endpoint** in `src/api/v1/endpoints/`

3. **Create and apply database migrations:**
   ```bash
   # Generate migration from schema changes
   supabase db diff -f initial_schema
   
   # Apply migrations locally
   supabase db reset
   
   # Deploy to remote when ready
   supabase db push
   ```

## Documentation

- Architecture: [../thesis/architecture/](../architecture/) (Quarto-based thesis documentation)
- Development Guide: [CLAUDE.md](CLAUDE.md)
- API Documentation: http://localhost:8000/docs (when running)

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, you can change the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change host port to 8001
```

### Database Connection Issues

Ensure the database service is healthy:

```bash
docker compose ps
docker compose logs api
```

### Hot Reload Not Working

Ensure the volume mounts are correctly configured in `docker-compose.yml` and that you're editing files in the mounted directories. The container will auto-reload when you make changes to Python files.

## License

This project is part of an academic thesis. See LICENSE file for details.

## Contact

For questions or issues, please open an issue on the repository.

