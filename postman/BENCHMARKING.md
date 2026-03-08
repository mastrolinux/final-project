# Backend Performance Benchmarking

Two complementary tools are available for measuring backend performance:
`hey` for raw HTTP load testing and Newman iterations for functional regression timing.

## Prerequisites

```bash
brew install hey           # HTTP load generator
npm install -g newman      # Postman CLI runner
```

## hey - Endpoint Load Testing

`hey` sends concurrent HTTP requests to a single endpoint and reports latency
distributions (p50, p95, p99), throughput (requests/sec), and status code breakdowns.

### Quick start

```bash
cd backend

# Baseline: health endpoint, 200 requests, 10 concurrent
./scripts/benchmark.sh

# Higher concurrency
./scripts/benchmark.sh -n 500 -c 20

# Sustained load for 30 seconds
./scripts/benchmark.sh -t 30s

# Include authenticated endpoints (login, context resolution, context list)
./scripts/benchmark.sh --auth

# Custom base URL (e.g. staging)
BASE_URL=https://identity-api-9hpf.onrender.com ./scripts/benchmark.sh
```

### Endpoints tested

Without `--auth`:
- `GET /health` - baseline with no database query
- `GET /health/detailed` - includes database and Redis connectivity check

With `--auth`:
- `POST /api/v1/auth/login` - Argon2id password hashing under load
- `GET /api/v1/profiles/{id}/contexts/{id}/resolved` - inheritance engine (O(n) resolution)
- `GET /api/v1/profiles/{id}/contexts` - context listing with pagination

### Interpreting results

The thesis target is p95 response time under 200ms. In `hey` output, look for:

```
Latency distribution:
  50% in X.XXXX secs
  75% in X.XXXX secs
  90% in X.XXXX secs
  95% in X.XXXX secs    <-- this is the target metric
  99% in X.XXXX secs
```

Status code distribution should show all 200s (or 401s for unauthenticated requests
to protected endpoints). Any 5xx responses indicate server errors under load.

## Newman - Functional Regression Timing

Newman runs the full Postman collection repeatedly. This measures average response
times across the entire API surface. Newman is single-threaded and sequential, so
it does not test concurrency. It validates that functional correctness holds across
repeated runs.

### Quick start

```bash
cd backend

```

### When to use which

Use `hey` when:
- Measuring raw throughput and latency under concurrent load
- Testing a specific endpoint in isolation
- Validating the p95 < 200ms target
- Stress-testing Argon2id hashing or database connection pooling

Use Newman iterations when:
- Verifying no functional regressions across the full API
- Generating JSON reports for automated analysis
- Testing end-to-end flows (authentication, context creation, resolution)
