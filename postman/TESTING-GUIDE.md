# Step-by-Step Testing Guide

Manual Testing with Postman, curl, and Email Verification via Mailpit.

## Prerequisites

### 1. Start Backend Services

```bash
cd /Users/lucacipriani/Devs/thesis/backend
./scripts/start.sh
```

Wait for all services to start. You should see:

```
API URL: http://127.0.0.1:8000
Database URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
Studio URL: http://127.0.0.1:54323
Mailpit URL: http://127.0.0.1:54324
```

### 2. Verify Services are Running

```bash
# Test API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2025-12-29T..."}
```

### 3. Open Mailpit Email UI

Open your browser and navigate to http://127.0.0.1:54324

You should see the Mailpit interface. This is where all test emails appear.

### 4. Import Postman Collection and Environment

1. Open Postman
2. Click **Import** (top left)
3. Select `thesis-api.postman_collection.json`
4. Click **Environments** (left sidebar) then **Import**
5. Select `thesis-local.postman_environment.json`
6. Select **"Thesis - Local Development"** environment from dropdown (top right)

## API Endpoints Reference

### Health Endpoints
- GET /health - Basic health check
- GET /health/detailed - Component health (database, tables)

### Profile Endpoints
- POST /api/v1/profiles - Create profile
- GET /api/v1/profiles/{user_id} - Get profile
- PATCH /api/v1/profiles/{user_id} - Update profile

### Context Endpoints
- POST /api/v1/profiles/{user_id}/contexts - Create context
- GET /api/v1/profiles/{user_id}/contexts - List contexts
- GET /api/v1/profiles/{user_id}/contexts/{context_id} - Get context (raw)
- GET /api/v1/profiles/{user_id}/contexts/{context_id}/resolved - Resolve profile
- PATCH /api/v1/profiles/{user_id}/contexts/{context_id} - Update context
- DELETE /api/v1/profiles/{user_id}/contexts/{context_id} - Delete context

### Authentication Endpoints (Implemented Dec 30, 2025)
- POST /api/v1/auth/register - User registration
- POST /api/v1/auth/login - User login (returns JWT tokens)
- POST /api/v1/auth/verify-email - Email verification
- POST /api/v1/auth/request-reset - Request password reset
- POST /api/v1/auth/reset-password - Reset password with token
- POST /api/v1/auth/resend-verification - Resend verification email
- POST /api/v1/auth/refresh - Refresh access token (token rotation)

## Phase 1: Health Checks

### Test 1: Basic Health Check

**Request:**
```bash
curl http://localhost:8000/health
```

**Expected Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-29T12:00:00Z"
}
```

### Test 2: Detailed Health Check

**Request:**
```bash
curl http://localhost:8000/health/detailed
```

**Expected Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-29T12:00:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "connection": true
    },
    "supabase": {
      "status": "healthy",
      "tables": ["base_profiles", "context_profiles", "identity_names", "auth_users"]
    }
  }
}
```

## Phase 2: Authentication Flow

### Test 3: Register New User

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!",
    "preferred_name": "Test User",
    "account_type": "unverified",
    "preferred_language": "en"
  }'
```

**Expected Response (201 Created):**
```json
{
  "user_id": "uuid-here",
  "email": "testuser@example.com",
  "is_email_verified": false,
  "message": "Registration successful. Please check your email to verify your account."
}
```

### Test 4: Check Mailpit for Verification Email

1. Open http://127.0.0.1:54324
2. You should see email with:
   - From: noreply@identity-api.local
   - To: testuser@example.com
   - Subject: "Verify your email address"

### Test 5: Get Verification Token

**From Database:**
```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT verification_token FROM auth_users WHERE email = 'testuser@example.com';"
```

**Or from Mailpit:** Click email, find verification link, extract token parameter.

### Test 6: Verify Email

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN_HERE"}'
```

**Expected Response (200 OK):**
```json
{
  "message": "Email verified successfully",
  "email": "",
  "user_id": ""
}
```

### Test 7: Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!"
  }'
```

**Expected Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "uuid-here",
  "email": "testuser@example.com",
  "is_email_verified": true,
  "account_type": "unverified"
}
```

### Test 8: Password Reset Flow

**Step 1: Request Reset**
```bash
curl -X POST http://localhost:8000/api/v1/auth/request-reset \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com"}'
```

**Step 2: Check Mailpit** for reset email with subject "Reset your password"

**Step 3: Get Reset Token**
```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT reset_token FROM auth_users WHERE email = 'testuser@example.com';"
```

**Step 4: Reset Password**
```bash
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_RESET_TOKEN",
    "new_password": "NewSecurePass456!"
  }'
```

**Step 5: Login with New Password**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "NewSecurePass456!"
  }'
```

### Test 9: Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN_FROM_LOGIN"}'
```

**Expected Response (200 OK):**
```json
{
  "access_token": "new-access-token...",
  "refresh_token": "new-refresh-token...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Note: Old refresh token is invalidated (token rotation security).

## Phase 3: Context Profile Creation

Use seed user Sarah Chen (user_id: 00000000-0000-0000-0000-000000000001) for these tests.

### Test 10: Create Professional Context

```bash
curl -X POST "http://localhost:8000/api/v1/profiles/00000000-0000-0000-0000-000000000001/contexts" \
  -H "Content-Type: application/json" \
  -d '{
    "context_type": "professional",
    "context_name": "Hospital Network",
    "display_name_override": "Dr. Sarah Chen, MD, PhD",
    "email_override": "s.chen@hospital.org",
    "bio": "Board-certified psychiatrist specializing in trauma and PTSD"
  }'
```

**Expected Response (201 Created):**
```json
{
  "id": "uuid-here",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "context_type": "professional",
  "context_name": "Hospital Network",
  "display_name_override": "Dr. Sarah Chen, MD, PhD",
  "email_override": "s.chen@hospital.org",
  "bio": "Board-certified psychiatrist specializing in trauma and PTSD",
  "is_active": true
}
```

### Test 11: Create Social Context

```bash
curl -X POST "http://localhost:8000/api/v1/profiles/00000000-0000-0000-0000-000000000001/contexts" \
  -H "Content-Type: application/json" \
  -d '{
    "context_type": "social",
    "context_name": "Fitness Apps",
    "display_name_override": "Sarah",
    "bio": "Health and wellness enthusiast. Loves running and yoga."
  }'
```

## Phase 4: Profile Resolution (Inheritance Engine)

### Test 12: Resolve Context with Partial Overrides

This is the critical test that validates the inheritance algorithm.

**Step 1: Create context with only email override**
```bash
curl -X POST "http://localhost:8000/api/v1/profiles/00000000-0000-0000-0000-000000000001/contexts" \
  -H "Content-Type: application/json" \
  -d '{
    "context_type": "professional",
    "context_name": "LinkedIn",
    "email_override": "sarah.chen.linkedin@example.com"
  }'
```

**Step 2: Resolve the profile** (replace CONTEXT_ID with actual ID from step 1)
```bash
curl "http://localhost:8000/api/v1/profiles/00000000-0000-0000-0000-000000000001/contexts/CONTEXT_ID/resolved"
```

**Expected Resolution Response:**
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "context_id": "uuid-here",
  "context_type": "professional",
  "context_name": "LinkedIn",
  "display_name": "Dr. Sarah Chen",
  "email": "sarah.chen.linkedin@example.com",
  "phone": "+1-555-0101",
  "bio": null,
  "preferred_language": "en",
  "account_type": "verified"
}
```

**Critical Verification:**
- Email is OVERRIDDEN: "sarah.chen.linkedin@example.com"
- Phone is INHERITED: "+1-555-0101" (from base_profiles.primary_phone)
- Display name is INHERITED: "Dr. Sarah Chen" (from base profile)

This proves the inheritance engine works correctly.

## Phase 5: Context Isolation Validation

This validates the core thesis contribution: context collapse prevention.

### Test 13: Validate Professional and Social Separation

After creating professional and social contexts, resolve both and verify:

**Professional Context:**
- display_name: "Dr. Sarah Chen, MD, PhD"
- email: "s.chen@hospital.org"
- bio: Contains "psychiatrist", "MD", "PhD"

**Social Context:**
- display_name: "Sarah"
- email: "sarah.chen@example.com" (inherited)
- bio: Contains "wellness", "yoga"

**Proof:** Professional credentials do not leak to social context, and personal wellness info does not appear in professional context.

## Phase 6: Business Rules Validation

### Test 14: Pseudonymous Account Restrictions

Use Alex (user_id: 00000000-0000-0000-0000-000000000003, account_type: pseudonymous)

```bash
curl -X POST "http://localhost:8000/api/v1/profiles/00000000-0000-0000-0000-000000000003/contexts" \
  -H "Content-Type: application/json" \
  -d '{
    "context_type": "legal",
    "context_name": "Government Services"
  }'
```

**Expected Response (403 Forbidden):**
```json
{
  "detail": {
    "error": "FORBIDDEN",
    "message": "Pseudonymous accounts cannot create legal or healthcare contexts",
    "user_id": "00000000-0000-0000-0000-000000000003",
    "account_type": "pseudonymous",
    "attempted_context": "legal"
  }
}
```

## Authentication Error Testing

### Test Weak Password

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "weak@example.com", "password": "weak", "preferred_name": "Weak"}'
```

**Expected:** 422 Validation Error (password too short)

### Test Duplicate Email

```bash
# Register first
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "dup@example.com", "password": "SecurePass123!", "preferred_name": "First"}'

# Try again
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "dup@example.com", "password": "DifferentPass123!", "preferred_name": "Second"}'
```

**Expected:** 409 Conflict (email already registered)

### Test Invalid Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "nonexistent@example.com", "password": "WrongPass123!"}'
```

**Expected:** 401 Unauthorized

## Seed Data Reference

The database includes 5 sample users from `backend/supabase/seed.sql`:

| User | Email | Account Type | Email Verified | Notes |
|------|-------|--------------|----------------|-------|
| Sarah Chen | sarah.chen@example.com | verified | Yes | Main test user |
| Li Ming | li.ming@example.com | unverified | No | Has stub verification token |
| Alex | alex.anonymous@protonmail.com | pseudonymous | Yes | Cannot create legal contexts |
| Sukarno | sukarno@example.id | verified | Yes | Mononym example |
| Jordan Smith | jordan.smith@example.com | verified | Yes | Name change example |

### Testing Li Ming's Email Verification

Li Ming has an unverified email with stub token:

```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT email, is_email_verified, verification_token FROM auth_users WHERE email = 'li.ming@example.com';"
```

Token: `stub-verification-token-li-ming-001`

## Quick Verification Commands

```bash
# Check auth_users table
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT email, is_email_verified, verification_token IS NOT NULL as has_token 
   FROM auth_users ORDER BY created_at DESC LIMIT 5;"

# Count emails in Mailpit
curl -s http://127.0.0.1:54324/api/v1/messages | jq '.total'

# Check Celery worker status
docker compose logs celery_worker | grep "ready\|Task.*succeeded" | tail -5

# Check SMTP port
nc -zv 127.0.0.1 54325
```

## Troubleshooting

### Tests Fail with 404 Errors

**Cause:** Backend services not running

**Solution:**
```bash
cd backend
./scripts/start.sh
./scripts/status.sh
```

### Tests Fail with 409 Conflicts

**Cause:** Context names already exist

**Solution:**
```bash
cd backend
./scripts/reset.sh
```

### No Email in Mailpit

**Check Celery worker:**
```bash
docker compose logs celery_worker | grep "Task send_verification_email"
```

Should see: `Task send_verification_email[...] succeeded`

**Check SMTP port:**
```bash
nc -zv 127.0.0.1 54325
```

### Login Returns 401

- Check password is correct
- Check user exists in database
- Check account not locked (`locked_until` should be NULL or past)

### Verification Token Invalid

- Check token not expired (24 hours from registration)
- Check token not already used (gets cleared after verification)
- Use resend-verification endpoint for fresh token

## Postman Collection Structure

The Postman collection is organized into folders:

1. **01 - Health Checks** - Basic and detailed health
2. **02 - Create Context Profile** - Context creation with validation
3. **03 - List User Contexts** - Retrieve all contexts for a user
4. **04 - Get Resolved Profile** - Inheritance engine validation
5. **05 - Update Context Profile** - Modify existing contexts
6. **06 - Delete Context Profile** - Remove contexts
7. **07 - End-to-End Scenarios** - Full workflow demonstration
8. **08 - Authentication** - Register, login, verify, reset, refresh

### Adding Authentication Requests to Postman

**Pre-Request Script for Register:**
```javascript
const timestamp = Date.now();
pm.collectionVariables.set("test_email", `testuser${timestamp}@example.com`);
pm.collectionVariables.set("test_password", "SecurePass123!");
```

**Test Script for Login:**
```javascript
pm.test("Response has JWT tokens", function() {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("access_token");
    pm.expect(jsonData).to.have.property("refresh_token");
    pm.collectionVariables.set("access_token", jsonData.access_token);
    pm.collectionVariables.set("refresh_token", jsonData.refresh_token);
});
```

## Test Coverage Summary

### Implemented and Tested

- Health checks (basic and detailed)
- User registration with email verification
- Login with JWT tokens (access + refresh)
- Password reset flow
- Token refresh with rotation
- Context profile CRUD operations
- Profile inheritance engine
- Context resolution with partial overrides
- Context isolation (context collapse prevention)
- Business rules (pseudonymous restrictions)
- Seed data with 5 diverse users

### Key Validation Points

1. **Inheritance Engine**: Null overrides inherit from base profile
2. **Context Isolation**: Professional and social contexts remain separate
3. **Business Rules**: Pseudonymous accounts cannot create legal contexts
4. **1:1 Relationship**: Each base_profile has exactly one auth_users record
5. **Email Infrastructure**: Mailpit captures emails for testing
6. **Token Rotation**: Refresh tokens are single-use (blacklisted after use)

## Resources

- **Postman Collection**: `postman/thesis-api.postman_collection.json`
- **Environment File**: `postman/thesis-local.postman_environment.json`
- **Backend Tests**: `backend/tests/integration/`
- **Seed Data**: `backend/supabase/seed.sql`
- **Mailpit UI**: http://127.0.0.1:54324
- **API Docs**: http://localhost:8000/docs
- **Auth Schemas**: `backend/src/schemas/auth.py`
- **Auth Endpoints**: `backend/src/api/v1/endpoints/auth.py`

For questions or issues, refer to `CLAUDE.md` and `backend/TESTING.md`.
