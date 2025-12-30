# Quick Test Commands - Postman CLI (Newman)

## Prerequisites

```bash
# Install Newman
npm install -g newman

# Start backend services
cd ../backend
./scripts/start.sh

# Verify services
curl http://localhost:8000/health
```

## Run Complete Test Suite

```bash
cd /Users/lucacipriani/Devs/thesis/postman

# Run all tests
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --reporters cli,json \
  --reporter-json-export test-results.json

# Run with detailed output
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --reporters cli \
  --color on \
  --delay-request 500
```

## Run Individual Test Folders

### 1. Health Checks

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --folder "01 - Health Checks"
```

**What this tests:**
- Basic API connectivity
- Database health
- Component status (auth_users table presence)

---

### 2. Create Context Profile

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --folder "02 - Create Context Profile"
```

**What this tests:**
- Professional context creation
- Social context creation
- Business rule: pseudonymous restrictions
- Validation: nonexistent user handling

---

### 3. List User Contexts

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --folder "03 - List User Contexts"
```

**What this tests:**
- Retrieve all contexts for a user
- Pagination and filtering

---

### 4. Get Resolved Profile (CRITICAL - Inheritance Engine)

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --folder "04 - Get Resolved Profile (CRITICAL)"
```

**What this tests:**
- **MOST IMPORTANT TEST**
- Profile resolution with full overrides
- Profile resolution with partial overrides
- **Inheritance validation**: Null fields inherit from base profile
- Base profile resolution (no context)

**Key Validation:**
```javascript
// Creates context with ONLY email override
// Verifies phone is inherited from base profile
// This proves the inheritance engine works!
```

---

### 5. Update Context Profile

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --folder "05 - Update Context Profile"
```

**What this tests:**
- Modify existing context overrides
- Validation of update operations

---

### 6. Delete Context Profile

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --folder "06 - Delete Context Profile"
```

**What this tests:**
- Soft delete of contexts
- deleted_at timestamp handling

---

### 7. End-to-End Scenarios (Context Collapse Prevention)

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --folder "07 - End-to-End Scenarios"
```

**What this tests:**
- **THESIS CONTRIBUTION VALIDATION**
- Create professional context (Dr. Sarah Chen with credentials)
- Create social context (Sarah with wellness info)
- Resolve both contexts
- **Validate context isolation**: Professional credentials hidden from social, personal info hidden from professional

**This proves context collapse prevention works!**

---

## Check Test Results

```bash
# View JSON results
cat test-results.json | jq '.run.stats'

# Count passed/failed tests
cat test-results.json | jq '.run.stats.tests'

# View specific test failures
cat test-results.json | jq '.run.failures[]'
```

## Run Tests with Specific Options

### Stop on First Failure

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --bail
```

### Run with Delay Between Requests

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --delay-request 1000  # 1 second delay
```

### Run Specific Number of Iterations

```bash
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  -n 3  # Run 3 times
```

### Export Results to HTML

```bash
# Install HTML reporter
npm install -g newman-reporter-html

# Run with HTML report
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --reporters cli,html \
  --reporter-html-export test-report.html

# Open report in browser
open test-report.html  # macOS
# xdg-open test-report.html  # Linux
```

---

## Check Mailpit for Emails (Manual)

While Newman runs tests in CLI, open Mailpit UI in browser to see captured emails:

```bash
# Open Mailpit UI
open http://127.0.0.1:54324  # macOS
# xdg-open http://127.0.0.1:54324  # Linux
```

### Check Emails via Mailpit API

```bash
# List all emails
curl http://127.0.0.1:54324/api/v1/messages | jq

# Get specific email
curl http://127.0.0.1:54324/api/v1/messages/{message_id} | jq

# Delete all emails
curl -X DELETE http://127.0.0.1:54324/api/v1/messages
```

---

## Database Verification Commands

### Check auth_users Table

```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT email, is_email_verified, verification_token FROM auth_users ORDER BY email;"
```

### Check Li Ming's Unverified Status

```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT email, is_email_verified, verification_token, verification_token_expires_at FROM auth_users WHERE email = 'li.ming@example.com';"
```

**Expected Output:**
```
        email         | is_email_verified |         verification_token          | verification_token_expires_at
----------------------+-------------------+-------------------------------------+-------------------------------
 li.ming@example.com  | f                 | stub-verification-token-li-ming-001 | 2026-12-31 23:59:59+00
```

### Check Context Profiles Created

```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT user_id, context_type, context_name, is_active FROM context_profiles WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 10;"
```

### Verify Inheritance (Join Query)

```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT 
    bp.primary_email as base_email,
    bp.primary_phone as base_phone,
    cp.email_override as context_email,
    cp.phone_override as context_phone,
    COALESCE(cp.email_override, bp.primary_email) as resolved_email,
    COALESCE(cp.phone_override, bp.primary_phone) as resolved_phone
  FROM context_profiles cp
  JOIN base_profiles bp ON cp.user_id = bp.user_id
  WHERE cp.deleted_at IS NULL
  LIMIT 5;"
```

---

## Reset Database Between Test Runs

```bash
cd ../backend
./scripts/reset.sh

# Verify reset
curl http://localhost:8000/health/detailed | jq '.components.supabase.tables'
```

---

## CI/CD Integration Example

```yaml
# .github/workflows/api-tests.yml
name: API Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Start Backend Services
        run: |
          cd backend
          ./scripts/start.sh
      
      - name: Install Newman
        run: npm install -g newman
      
      - name: Run Postman Tests
        run: |
          cd postman
          newman run thesis-api.postman_collection.json \
            -e thesis-local.postman_environment.json \
            --reporters cli,json \
            --reporter-json-export newman-results.json
      
      - name: Upload Test Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: newman-results
          path: postman/newman-results.json
```

---

## Useful Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Postman/Newman aliases
alias newman-run='newman run thesis-api.postman_collection.json -e thesis-local.postman_environment.json'
alias newman-test='newman-run --reporters cli,html --reporter-html-export test-report.html && open test-report.html'
alias mailpit-open='open http://127.0.0.1:54324'
alias api-health='curl http://localhost:8000/health/detailed | jq'
```

Then use:
```bash
newman-run
newman-test
mailpit-open
api-health
```

---

## Summary of Critical Tests

| Test | Command | Validates |
|------|---------|-----------|
| **Inheritance Engine** | `--folder "04 - Get Resolved Profile (CRITICAL)"` | Null overrides inherit from base |
| **Context Isolation** | `--folder "07 - End-to-End Scenarios"` | Context collapse prevention |
| **Business Rules** | `--folder "02 - Create Context Profile"` | Pseudonymous restrictions |
| **Complete Suite** | `newman run ...` (no folder flag) | All 20+ tests |

---

## For Step-by-Step Manual Testing

Use Postman GUI for detailed exploration. See:
- **`TESTING-GUIDE.md`** - Comprehensive step-by-step guide
- **`README.md`** - Quick start and overview

---

## Resources

- **Postman Collection**: `thesis-api.postman_collection.json`
- **Environment**: `thesis-local.postman_environment.json`
- **Detailed Guide**: `TESTING-GUIDE.md`
- **Newman Docs**: https://learning.postman.com/docs/running-collections/using-newman-cli/
- **Mailpit UI**: http://127.0.0.1:54324
- **API Docs**: http://localhost:8000/docs

