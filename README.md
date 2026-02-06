# Identity and Profile Management API - Final Project

> **Academic Thesis Project**: A comprehensive demonstration of context-aware digital identity management with independently deployable backend and frontend services.

## Project Overview

This **monorepo** contains a complete implementation and documentation of an identity management platform that respects cultural diversity, privacy, and context-dependent identity presentation.

### What This Project Solves

People present themselves differently in different contexts:

- **Professional**: Dr. Sarah Chen, Board-Certified Psychiatrist
- **Social**: Sarah C., Book lover and photographer
- **Family**: Mom, wife, weekend adventurer

This system provides secure, privacy oriented infrastructure for managing these multiple identity presentations.

## Repository Structure

```
final-project/
├── backend/              # FastAPI backend service -> Render.com
│   ├── src/             # Python source code
│   ├── tests/           # Test suite (pytest)
│   ├── supabase/        # Database configuration
│   ├── Dockerfile       # Container definition
│   └── README.md        # Backend documentation
│
├── frontend/            # Frontend application -> Render.com
│   ├── src/             # Vue.js/React source (to be implemented)
│   ├── package.json     # Dependencies
│   └── README.md        # Frontend documentation
│
├── architecture/        # Thesis chapters (Quarto)
│   ├── original-problem.qmd
│   ├── overview.qmd
│   ├── system-context.qmd
│   ├── component-architecture.qmd
│   ├── context-resolution.qmd
│   ├── data-architecture.qmd
│   ├── security-architecture.qmd
│   ├── integration-architecture.qmd
│   ├── deployment-operations.qmd
│   └── decisions-future.qmd
│
├── _quarto.yml         # Thesis configuration
├── index.qmd           # Thesis introduction
├── references.bib      # Bibliography (BibTeX)
├── render.yaml         # Deployment config (both services)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Quick Start

### Backend API

```bash
cd backend
./script/start.sh

# Access:
# - API: http://localhost:8000
# - Swagger Docs: http://localhost:8000/docs
# - Supabase Studio: http://127.0.0.1:54323
```

**Details**: See [backend/README.md](backend/README.md)

### Frontend Application

```bash
cd frontend
npm install
npm run dev
```

**Details**: See [frontend/README.md](frontend/README.md)

### Thesis Documentation

```bash
# Preview in browser (auto-reload)
quarto preview

# Generate PDF
quarto render --to pdf

# Generate HTML
quarto render --to html
```

**Output**: `_book/Identity-and-Profile-Management-API.pdf`

## System Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │────────>│   Backend    │────────>│  Supabase   │
│  (Vue.js)   │  HTTPS  │   (FastAPI)  │  SQL    │ (PostgreSQL)│
│             │<────────│              │<────────│             │
└─────────────┘   JSON  └──────────────┘  Data   └─────────────┘
      │                        │
      │                        │
      v                        v
┌─────────────┐         ┌──────────────┐
│  Render.com │         │  Render.com  │
│   Frontend  │         │   Backend    │
└─────────────┘         └──────────────┘
```

### Key Features

- **Multi-Context Identity**: Professional, social, family, healthcare contexts
- **Cultural Neutrality**: No assumptions about Western naming conventions
- **GDPR Consideration**: attempt to respect Article 15-22 data subject rights
- **OAuth 2.1**: Third-party integration with scope-based access control
- **Multilingual**: Store and present names in multiple languages

## Technology Stack

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI (async, OpenAPI docs)
- **Database**: PostgreSQL 15+ via Supabase
- **Authentication**: Supabase Auth + JWT
- **Deployment**: Render.com (Docker containers)
- **Testing**: pytest, pytest-cov (>80% coverage)

### Frontend (Planned)
- **Framework**: Vue.js 3 or React
- **Build Tool**: Vite
- **Language**: TypeScript
- **State**: Pinia or Redux
- **Deployment**: Render.com
- **Testing**: Vitest, Cypress

### Thesis
- **Generator**: Quarto
- **Format**: Markdown (.qmd)
- **Bibliography**: BibTeX
- **Output**: PDF (LaTeX) + HTML

## Deployment

### Backend -> Render.com

**Configuration**: `render.yaml` (root level)

```yaml
services:
  - type: web
    name: identity-api-backend
    rootDir: backend
    env: python
```

**Deployment**:

- Auto-deploy from `main` branch
- Environment: Production PostgreSQL (Supabase)
- Scaling: Auto-scale based on load

**Live URL**: `https://identity-api-backend.onrender.com`

### Frontend -> Render.com (When Ready)

**Configuration**: Commented out in `render.yaml`

Uncomment and configure when frontend is implemented.

### Thesis -> GitHub Pages (Optional)

HTML version can be published to GitHub Pages.

## Project Status

| Component | Status | Progress |
|-----------|--------|----------|
| Architecture Docs | Complete | 100% |
| Thesis Structure | Complete | 100% |
| Backend API | In Progress | 40% |
| Database Schema | In Progress | 60% |
| Frontend UI | Planned | 0% |
| Integration Tests | Planned | 0% |
| OAuth Implementation | Planned | 0% |
| GDPR Considerations | Planned | 0% |

## Academic Context

**Course**: CM3070 Computer Science Final Project
**Institution**: University of London

### Evaluation Criteria Alignment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Strong requirements with research | Complete | Architecture documentation |
| Solid security and privacy (GDPR) | Complete | Security architecture, GDPR design |
| Data model beyond simplest cases | Complete | Multi-context, multilingual, temporal |
| Robust, widely applicable API | Complete | RESTful design, OAuth 2.0 |
| Frontend demonstrating use cases | Planned | Vue.js SPA |

## Development Workflow

### Working on Backend

```bash
cd backend
docker compose up -d       # Start services
docker compose logs -f     # View logs
docker compose exec api pytest  # Run tests
```

### Working on Frontend

```bash
cd frontend
npm run dev               # Development server
npm run build            # Production build
npm run test             # Run tests
```

### Working on Thesis

```bash
quarto preview           # Live preview
quarto render           # Generate PDF/HTML
```

### Committing Changes

```bash
# Make changes across backend, frontend, docs
git add backend/ frontend/ architecture/
git commit -m "Implement user authentication

- Backend: Add JWT authentication endpoints
- Frontend: Add login/logout UI components  
- Thesis: Document authentication architecture
"
git push
```

## Documentation

### For Developers
- [Backend Setup](backend/README.md) - API development
- [API Docs](http://localhost:8000/docs) - OpenAPI/Swagger

### For Thesis Review
- [Architecture](architecture/) - Complete system design
- [Quarto Thesis](index.qmd) - Thesis introduction
- [References](references.bib) - Bibliography

### For DevOps
- [Deployment](render.yaml) - Service configuration

## Monorepo Benefits

### Why This Structure?

- Version Coherence: Frontend, backend, docs always in sync
- Atomic Changes: Update API + UI + docs in single commit
- Shared History: See how system evolved together
- Easier Review: Supervisors see complete project
- Independent Deploy: Each service deploys separately
- GitHub Showcase: One repo shows all skills

## Author

**Luca Cipriani**
GitHub: [@mastrolinux](https://github.com/mastrolinux)

## License

This project is submitted as academic coursework.
See [LICENSE](LICENSE) for details.

## Getting Started (New Developers)

```bash
# 1. Clone the repository
git clone https://github.com/mastrolinux/final-project.git
cd final-project

# 2. Start backend
cd backend
supabase start
docker compose up -d

# 3. Preview thesis
cd ..
quarto preview

# 4. Access services
# Backend API: http://localhost:8000/docs
# Supabase: http://127.0.0.1:54323
# Mailpit: http://127.0.0.1:54324/
```

**Note**: This is a monorepo. Backend, frontend, and thesis documentation are all in this single repository for version coherence and easier academic review.
