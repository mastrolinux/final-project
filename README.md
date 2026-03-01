# Identity and Profile Management API - Final Project

![CI](https://github.com/mastrolinux/final-project/actions/workflows/ci.yml/badge.svg)

> Academic thesis project (CM3070, University of London): a context-aware digital identity management platform with independently deployable backend and frontend services.

## What This Project Solves

People present themselves differently in different contexts:

- Professional: Dr. Sarah Chen, Board-Certified Psychiatrist
- Social: Sarah C., Book lover and photographer
- Family: Mom, wife, weekend adventurer

Current identity systems force a single representation. This platform provides secure, privacy-oriented infrastructure for managing multiple identity presentations across cultural, contextual, and regulatory boundaries.

## Project Status

- Phases 1-4 complete (Auth, Context Profiles, OAuth 2.1, Privacy Features)
- Phase 5 (Frontend) in progress, Phase 6 (Deployment) next
- 751 automated tests, 85% coverage
- 19 database migrations applied
- CI/CD via GitHub Actions (ruff, mypy, bandit, pytest, vue-tsc, eslint, vitest)

## Repository Structure

```
final-project/
├── backend/              # FastAPI API service
│   ├── src/              # Python source (72 files, ~14.6K LOC)
│   ├── tests/            # pytest suite (46 files, ~16.9K LOC)
│   ├── supabase/         # Migrations and seed data
│   └── scripts/          # start.sh, stop.sh, reset.sh, status.sh
├── frontend/             # Vue 3 + TypeScript SPA
│   ├── src/              # Components, views, services (~25.2K LOC)
│   └── e2e/              # End-to-end tests
├── architecture/         # Thesis chapters (Quarto .qmd)
├── postman/              # API collection and environments
├── draft-report.qmd      # Final report source
├── render.yaml           # Render.com deployment config
└── .github/workflows/    # CI/CD pipelines
```

## Quick Start

### Backend

```bash
cd backend
cp env.local.template .env
./scripts/start.sh

# API: http://localhost:8000/docs
# Supabase Studio: http://127.0.0.1:54323
# Mailpit: http://127.0.0.1:54324
```

### Frontend

```bash
cd frontend
npm install && npm run dev

# App: http://localhost:3000
```

### Thesis

```bash
quarto preview              # Live preview
quarto render --to pdf      # Generate PDF
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy |
| Database | PostgreSQL 15+ (Supabase), Redis |
| Auth | Custom JWT (HS256) + OAuth 2.1 with PKCE |
| Frontend | Vue 3, TypeScript, Vite, Pinia |
| Testing | pytest (backend), vitest (frontend) |
| Quality | ruff, mypy, bandit, eslint, vue-tsc |
| Deployment | Render.com, GitHub Actions CI/CD |
| Thesis | Quarto, LaTeX, BibTeX |

## Key Features

- Multi-context identity with inheritance engine (O(n) resolution)
- Cultural neutrality via JSONB multilingual name storage
- GDPR-inspired privacy: data export, soft deletion, audit logging
- OAuth 2.1 authorization server with mandatory PKCE
- Identity document verification with Fernet encryption at rest
- Automated document expiry via Celery Beat
- Row-Level Security at the database layer

## Deployment

Configuration in `render.yaml`. CI runs on every push and pull request; auto-deploy from `main` via GitHub Actions.

Live URL: `https://identity.okrbusiness.com`

## Documentation

- [Backend setup and API guide](backend/README.md)
- [API reference (Swagger)](http://localhost:8000/docs)
- [Testing guide](backend/TESTING.md)
- [Postman collection](postman/README.md)
- [Architecture chapters](architecture/)
- [Deployment config](render.yaml)

## Author

Luca Cipriani - [@mastrolinux](https://github.com/mastrolinux)

## License

Submitted as academic coursework. Will be released as open source after graduation.
