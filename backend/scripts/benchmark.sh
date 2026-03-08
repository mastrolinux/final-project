#!/usr/bin/env bash
# benchmark.sh - HTTP load testing with hey
#
# Prerequisites: brew install hey
#
# Usage:
#   ./scripts/benchmark.sh                    # defaults: 200 requests, 10 concurrent
#   ./scripts/benchmark.sh -n 500 -c 20       # custom request count and concurrency
#   ./scripts/benchmark.sh -t 30s             # sustained load for 30 seconds
#   ./scripts/benchmark.sh --auth             # include authenticated endpoints

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
REQUESTS=200
CONCURRENCY=10
DURATION=""
RUN_AUTH=false

# Seed data IDs
SARAH_USER_ID="00000000-0000-0000-0000-000000000001"
PROF_CONTEXT_ID="20000000-0000-0000-0000-000000000001"

usage() {
    echo "Usage: $0 [-n requests] [-c concurrency] [-t duration] [--auth]"
    echo ""
    echo "Options:"
    echo "  -n NUM      Number of requests (default: 200)"
    echo "  -c NUM      Concurrency level (default: 10)"
    echo "  -t DURATION Sustained load duration, e.g. 30s (overrides -n)"
    echo "  --auth      Include authenticated endpoints (requires running backend with seed data)"
    echo "  -h          Show this help"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -n) REQUESTS="$2"; shift 2 ;;
        -c) CONCURRENCY="$2"; shift 2 ;;
        -t) DURATION="$2"; shift 2 ;;
        --auth) RUN_AUTH=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if ! command -v hey &> /dev/null; then
    echo "Error: hey is not installed. Install with: brew install hey"
    exit 1
fi

# Build hey arguments
HEY_ARGS="-c $CONCURRENCY"
if [[ -n "$DURATION" ]]; then
    HEY_ARGS="$HEY_ARGS -z $DURATION"
else
    HEY_ARGS="$HEY_ARGS -n $REQUESTS"
fi

echo "============================================"
echo "Backend Benchmark Suite"
echo "============================================"
echo "Base URL:    $BASE_URL"
if [[ -n "$DURATION" ]]; then
    echo "Duration:    $DURATION"
else
    echo "Requests:    $REQUESTS"
fi
echo "Concurrency: $CONCURRENCY"
echo "Auth tests:  $RUN_AUTH"
echo "============================================"
echo ""

# --- Unauthenticated endpoints ---

echo ">>> GET /health (baseline, no DB query)"
echo "--------------------------------------------"
# shellcheck disable=SC2086
hey $HEY_ARGS "$BASE_URL/health"
echo ""

echo ">>> GET /health/detailed (includes DB round-trip)"
echo "--------------------------------------------"
# shellcheck disable=SC2086
hey $HEY_ARGS "$BASE_URL/health/detailed"
echo ""

# --- Authenticated endpoints ---

if [[ "$RUN_AUTH" == true ]]; then
    echo ">>> POST /api/v1/auth/login (Argon2id hashing)"
    echo "--------------------------------------------"
    # shellcheck disable=SC2086
    hey $HEY_ARGS -m POST \
        -H "Content-Type: application/json" \
        -d '{"email":"sarah.chen@example.com","password":"SecurePass123!"}' \
        "$BASE_URL/api/v1/auth/login"
    echo ""

    # Obtain a token for authenticated GET requests
    echo "Obtaining auth token for authenticated endpoints..."
    TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"sarah.chen@example.com","password":"SecurePass123!"}' \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

    if [[ -z "$TOKEN" ]]; then
        echo "Warning: could not obtain auth token. Skipping authenticated GET endpoints."
    else
        echo ">>> GET /api/v1/profiles/{id}/contexts/{id}/resolved (inheritance engine)"
        echo "--------------------------------------------"
        # shellcheck disable=SC2086
        hey $HEY_ARGS \
            -H "Authorization: Bearer $TOKEN" \
            "$BASE_URL/api/v1/profiles/$SARAH_USER_ID/contexts/$PROF_CONTEXT_ID/resolved"
        echo ""

        echo ">>> GET /api/v1/profiles/{id}/contexts (list contexts)"
        echo "--------------------------------------------"
        # shellcheck disable=SC2086
        hey $HEY_ARGS \
            -H "Authorization: Bearer $TOKEN" \
            "$BASE_URL/api/v1/profiles/$SARAH_USER_ID/contexts"
        echo ""
    fi
fi

echo "============================================"
echo "Benchmark complete."
echo "============================================"
