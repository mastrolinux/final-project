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

### 1. Clone the Repository

```bash
git clone <repository-url>
cd thesis/backend
```

### 2. Install Supabase CLI (if not already installed)

```bash
# macOS
brew install supabase/tap/supabase

# Other platforms: https://supabase.com/docs/guides/cli
```

### 3. Start Supabase

```bash
supabase start
```

This will start all Supabase services:
- PostgreSQL database on port 54322
- Supabase Studio (UI) on http://127.0.0.1:54323
- API on http://127.0.0.1:54321

Note the connection details displayed after startup - you'll need them for the next step.

### 4. Set Up Environment Variables

```bash
cp .env.example .env
```

Update `.env` with the Supabase keys from `supabase status`:
- `SUPABASE_ANON_KEY` - the publishable (anon) key
- `SUPABASE_SERVICE_KEY` - the secret (service role) key

### 5. Start the FastAPI Application

```bash
docker compose up -d
```

This will start:
- FastAPI application on http://localhost:8000

### 6. Verify the Installation

Visit http://localhost:8000 in your browser. You should see the API welcome message.

**Available Services:**
- API: http://localhost:8000
- API Documentation (Swagger): http://localhost:8000/docs
- API Documentation (ReDoc): http://localhost:8000/redoc  
- Supabase Studio: http://127.0.0.1:54323
- Mailpit (Email Testing): http://127.0.0.1:54324

### 7. Check Health Status

```bash
curl http://localhost:8000/health
```

## Development Workflow

### Managing Services

**Supabase:**
```bash
# Start Supabase
supabase start

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
docker-compose logs

# Follow logs
docker-compose logs -f

# View API logs only
docker-compose logs -f api

# View database logs only
docker-compose logs -f db
```

### Running Commands Inside Container

```bash
# Access API container shell
docker-compose exec api bash

# Run tests
docker-compose exec api pytest

# Run tests with coverage
docker-compose exec api pytest --cov=src --cov-report=term-missing
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
docker-compose exec api mypy src/

# Linting
docker-compose exec api ruff check src/

# Format code
docker-compose exec api black src/

# Security scanning
docker-compose exec api bandit -r src/
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
├── .env.example            # Environment variables template
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

If port 8000 or 5432 is already in use, you can change the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change host port to 8001
```

### Database Connection Issues

Ensure the database service is healthy:

```bash
docker-compose ps
docker-compose logs db
```

### Hot Reload Not Working

Ensure the volume mounts are correctly configured in `docker-compose.yml` and that you're editing files in the mounted directories.

## License

This project is part of an academic thesis. See LICENSE file for details.

## Contact

For questions or issues, please open an issue on the repository.

