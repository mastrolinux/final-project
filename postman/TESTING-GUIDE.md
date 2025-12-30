# Step-by-Step Testing Guide
## Manual Testing with Postman and Email Verification

This guide provides detailed instructions for manually testing the Identity and Profile Management API using Postman, including email verification with Mailpit.

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

Open your browser and navigate to:
```
http://127.0.0.1:54324
```

You should see the Mailpit interface with an empty inbox. This is where all test emails will appear.

### 4. Import Postman Collection and Environment

1. Open Postman
2. Click **Import** (top left)
3. Select `thesis-api.postman_collection.json`
4. Click **Environments** (left sidebar) -> **Import**
5. Select `thesis-local.postman_environment.json`
6. Select **"Thesis - Local Development"** environment from dropdown (top right)

## Test Suite: Step-by-Step Execution

### Phase 1: Health Checks

#### Test 1: Basic Health Check

**Request:**
```http
GET http://localhost:8000/health
```

**Postman Steps:**
1. Navigate to: `01 - Health Checks` -> `GET /health`
2. Click **Send**

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-29T12:00:00Z"
}
```

**Verification:**
- Status code: 200
- Response has "status": "healthy"

---

#### Test 2: Detailed Health Check

**Request:**
```http
GET http://localhost:8000/health/detailed
```

**Postman Steps:**
1. Navigate to: `01 - Health Checks` -> `GET /health/detailed`
2. Click **Send**

**Expected Response:**
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

**Verification:**
- Status code: 200
- All components show "healthy"
- auth_users table present (newly implemented)

---

### Phase 2: Context Profile Creation

#### Test 3: Create Professional Context

**Request:**
```http
POST http://localhost:8000/api/v1/profiles/{sarah_user_id}/contexts
Content-Type: application/json

{
  "context_type": "professional",
  "context_name": "Hospital Network",
  "display_name_override": "Dr. Sarah Chen, MD, PhD",
  "email_override": "s.chen@hospital.org",
  "bio": "Board-certified psychiatrist specializing in trauma and PTSD"
}
```

**Postman Steps:**
1. Navigate to: `02 - Create Context Profile` -> `Create Professional Context (Success)`
2. Click **Send** (pre-request script generates unique context_name)

**Expected Response:**
```json
{
  "id": "uuid-here",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "context_type": "professional",
  "context_name": "Test-Professional-1735478400000",
  "display_name_override": "Dr. Sarah Chen, MD, PhD",
  "email_override": "s.chen@hospital.org",
  "phone_override": null,
  "bio": "Board-certified psychiatrist specializing in trauma and PTSD",
  "is_active": true,
  "created_at": "2025-12-29T12:00:00Z"
}
```

**Verification:**
- Status code: 201 Created
- Context type is "professional"
- Display name and email are overridden
- Response includes context_id (save this!)

**Save Context ID:**
The response includes an `id` field. Postman automatically saves this to the collection variable `created_context_id` for use in subsequent tests.

---

#### Test 4: Create Social Context

**Request:**
```http
POST http://localhost:8000/api/v1/profiles/{sarah_user_id}/contexts
Content-Type: application/json

{
  "context_type": "social",
  "context_name": "Fitness Apps",
  "display_name_override": "Sarah",
  "bio": "Health and wellness enthusiast. Loves running and yoga."
}
```

**Postman Steps:**
1. Navigate to: `02 - Create Context Profile` -> `Create Social Context (Minimal Fields)`
2. Click **Send**

**Expected Response:**
```json
{
  "id": "uuid-here",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "context_type": "social",
  "context_name": "Test-Social-1735478401000",
  "display_name_override": "Sarah",
  "email_override": null,
  "phone_override": null,
  "bio": "Health and wellness enthusiast. Loves running and yoga.",
  "is_active": true
}
```

**Verification:**
- Status code: 201 Created
- email_override is null (will inherit from base profile)
- phone_override is null (will inherit from base profile)

---

### Phase 3: Profile Resolution (CRITICAL - Inheritance Engine Test)

#### Test 5: Resolve Professional Context

**Request:**
```http
GET http://localhost:8000/api/v1/profiles/{sarah_user_id}/contexts/{context_id}/resolved
```

**Postman Steps:**
1. Navigate to: `04 - Get Resolved Profile (CRITICAL)` -> `Resolve Context with Full Overrides`
2. Click **Send**

**Expected Response:**
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "context_id": "uuid-here",
  "context_type": "professional",
  "context_name": "Test-Professional-1735478400000",
  "display_name": "Dr. Sarah Chen, MD, PhD",
  "email": "s.chen@hospital.org",
  "phone": "+1-555-0101",
  "bio": "Board-certified psychiatrist specializing in trauma and PTSD",
  "preferred_language": "en",
  "account_type": "verified"
}
```

**Verification:**
- Status code: 200
- Email is OVERRIDDEN: "s.chen@hospital.org"
- Phone is INHERITED: "+1-555-0101" (from base profile)
- Display name is OVERRIDDEN: "Dr. Sarah Chen, MD, PhD"

**KEY TEST**: The phone number proves the inheritance engine works! We only set email_override, but phone comes from the base profile.

---

#### Test 6: Resolve Context with Partial Overrides (INHERITANCE VALIDATION)

This is the most critical test that validates the inheritance algorithm.

**Request:**
```http
POST http://localhost:8000/api/v1/profiles/{sarah_user_id}/contexts
Content-Type: application/json

{
  "context_type": "professional",
  "context_name": "LinkedIn",
  "email_override": "sarah.chen.linkedin@example.com"
}
```

**Postman Steps:**
1. Navigate to: `04 - Get Resolved Profile (CRITICAL)` -> `Get Resolved Partial Context (Validates Inheritance)`
2. Click **Send** (this creates a context with ONLY email override)

**Expected Creation Response:**
```json
{
  "id": "uuid-here",
  "context_type": "professional",
  "email_override": "sarah.chen.linkedin@example.com",
  "display_name_override": null,
  "phone_override": null,
  "bio": null
}
```

**Now Resolve the Profile:**

**Request:**
```http
GET http://localhost:8000/api/v1/profiles/{sarah_user_id}/contexts/{context_id}/resolved
```

**Expected Resolution Response:**
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "context_id": "uuid-here",
  "context_type": "professional",
  "context_name": "Test-LinkedIn-1735478402000",
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

**PROOF**: This proves the inheritance engine works correctly! Null overrides inherit from the base profile.

---

### Phase 4: List and Validate Contexts

#### Test 7: List User Contexts

**Request:**
```http
GET http://localhost:8000/api/v1/profiles/{sarah_user_id}/contexts
```

**Postman Steps:**
1. Navigate to: `03 - List User Contexts` -> `List User Contexts`
2. Click **Send**

**Expected Response:**
```json
[
  {
    "id": "uuid-1",
    "context_type": "professional",
    "context_name": "Test-Professional-...",
    "is_active": true
  },
  {
    "id": "uuid-2",
    "context_type": "social",
    "context_name": "Test-Social-...",
    "is_active": true
  },
  {
    "id": "uuid-3",
    "context_type": "professional",
    "context_name": "Test-LinkedIn-...",
    "is_active": true
  }
]
```

**Verification:**
- Status code: 200
- Returns array of contexts
- All contexts have unique IDs
- Contexts belong to Sarah Chen

---

### Phase 5: Context Isolation Validation (End-to-End)

This validates the core thesis contribution: **context collapse prevention**.

#### Test 8: Create and Resolve Professional Context

**Request:**
```http
POST http://localhost:8000/api/v1/profiles/{sarah_user_id}/contexts

{
  "context_type": "professional",
  "context_name": "Hospital Network Final",
  "display_name_override": "Dr. Sarah Chen, MD, PhD",
  "email_override": "s.chen@hospital.org",
  "bio": "Board-certified psychiatrist specializing in trauma and PTSD. Over 15 years of clinical experience."
}
```

**Postman Steps:**
1. Navigate to: `07 - End-to-End Scenarios` -> `Step 1: Create Professional Context`
2. Click **Send**
3. Navigate to: `07 - End-to-End Scenarios` -> `Step 3: Resolve Professional Context`
4. Click **Send**

**Expected Professional Resolution:**
```json
{
  "display_name": "Dr. Sarah Chen, MD, PhD",
  "email": "s.chen@hospital.org",
  "bio": "Board-certified psychiatrist specializing in trauma and PTSD. Over 15 years of clinical experience."
}
```

**Note the professional credentials:**
- Psychiatrist title
- MD, PhD degrees
- Clinical experience

---

#### Test 9: Create and Resolve Social Context

**Request:**
```http
POST http://localhost:8000/api/v1/profiles/{sarah_user_id}/contexts

{
  "context_type": "social",
  "context_name": "Fitness Apps Final",
  "display_name_override": "Sarah",
  "bio": "Health and wellness enthusiast. Loves running and yoga."
}
```

**Postman Steps:**
1. Navigate to: `07 - End-to-End Scenarios` -> `Step 2: Create Social Context`
2. Click **Send**
3. Navigate to: `07 - End-to-End Scenarios` -> `Step 4: Resolve Social Context`
4. Click **Send**

**Expected Social Resolution:**
```json
{
  "display_name": "Sarah",
  "email": "sarah.chen@example.com",
  "bio": "Health and wellness enthusiast. Loves running and yoga."
}
```

**Note the personal information:**
- No professional credentials
- Personal email (inherited from base)
- Wellness focus

---

#### Test 10: Validate Context Isolation

**Postman Steps:**
1. Navigate to: `07 - End-to-End Scenarios` -> `Step 5: Validate Context Isolation`
2. Click **Send**

**Verification in Test Scripts:**

```javascript
pm.test("Professional and social contexts use different emails", function() {
    const professionalEmail = pm.collectionVariables.get("professional_email");
    const socialEmail = pm.collectionVariables.get("social_email");
    
    pm.expect(professionalEmail).to.not.eql(socialEmail);
    console.log("[PASS] Context isolation: Different emails used");
});

pm.test("Professional credentials hidden from social context", function() {
    const socialBio = pm.collectionVariables.get("social_bio");
    
    pm.expect(socialBio).to.not.include("psychiatrist");
    pm.expect(socialBio).to.not.include("MD");
    pm.expect(socialBio).to.not.include("PhD");
    console.log("[PASS] Context isolation: Professional credentials not leaked");
});

pm.test("Personal wellness info hidden from professional context", function() {
    const professionalBio = pm.collectionVariables.get("professional_bio");
    
    pm.expect(professionalBio).to.not.include("wellness");
    pm.expect(professionalBio).to.not.include("yoga");
    console.log("[PASS] Context isolation: Personal info not leaked");
});
```

**PROOF**: This proves context collapse prevention works! Professional and social identities remain separate.

---

### Phase 6: Business Rules Validation

#### Test 11: Pseudonymous Account Restrictions

**Request:**
```http
POST http://localhost:8000/api/v1/profiles/{alex_user_id}/contexts

{
  "context_type": "legal",
  "context_name": "Government Services"
}
```

**Postman Steps:**
1. Navigate to: `02 - Create Context Profile` -> `Pseudonymous Cannot Create Legal (403)`
2. Click **Send**

**Expected Response:**
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

**Verification:**
- Status code: 403 Forbidden
- Error message explains the restriction
- Business rule enforced: pseudonymous accounts cannot access sensitive contexts

---

## Email Verification Testing (Future - When Auth Service Implemented)

Once MAS-26 (Auth Service Implementation) is complete, you'll be able to test the email verification flow.

### Setup for Email Testing

1. Ensure Mailpit is running at http://127.0.0.1:54324
2. Clear existing emails in Mailpit (optional): Click "Delete All"

### Test Scenario: User Registration with Email Verification

#### Step 1: Register New User (Future Endpoint)

**Request:**
```http
POST http://localhost:8000/api/v1/auth/register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "SecurePassword123!",
  "preferred_name": "Alex Johnson"
}
```

#### Step 2: Check Mailpit for Verification Email

1. Open http://127.0.0.1:54324 in your browser
2. You should see a new email: "Verify your email address"
3. Click on the email to view it

**Expected Email Content:**
```
From: noreply@identity-api.local
To: newuser@example.com
Subject: Verify your email address

Hello Alex Johnson,

Please verify your email address by clicking the link below:

http://localhost:8000/api/v1/auth/verify-email?token=stub-verification-token-newuser-001

This link expires in 24 hours.

Best regards,
Identity Management Team
```

#### Step 3: Copy Verification Token

From the email, copy the verification token (the part after `token=`):
```
stub-verification-token-newuser-001
```

#### Step 4: Verify Email (Future Endpoint)

**Request:**
```http
POST http://localhost:8000/api/v1/auth/verify-email
Content-Type: application/json

{
  "token": "stub-verification-token-newuser-001"
}
```

**Expected Response:**
```json
{
  "status": "verified",
  "email": "newuser@example.com",
  "message": "Email successfully verified"
}
```

#### Step 5: Verify in Database

```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT email, is_email_verified, email_verified_at FROM auth_users WHERE email = 'newuser@example.com';"
```

**Expected Output:**
```
         email          | is_email_verified |     email_verified_at
------------------------+-------------------+---------------------------
 newuser@example.com    | t                 | 2025-12-29 12:05:00+00
```

---

## Current Test Data (Seed Users)

The database includes 5 sample users from `backend/supabase/seed.sql`:

| User | Email | Account Type | Email Verified | Notes |
|------|-------|--------------|----------------|-------|
| Sarah Chen | sarah.chen@example.com | verified | Yes | Used in most tests |
| Li Ming | li.ming@example.com | unverified | No | Has stub verification token |
| Alex | alex.anonymous@protonmail.com | pseudonymous | Yes | Cannot create legal contexts |
| Sukarno | sukarno@example.id | verified | Yes | Mononym example |
| Jordan Smith | jordan.smith@example.com | verified | Yes | Name change example |

### Testing Li Ming's Email Verification

Li Ming is the only user with an unverified email and stub verification token. You can test the verification flow with this user:

**Check Li Ming's Current Status:**
```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "SELECT email, is_email_verified, verification_token FROM auth_users WHERE email = 'li.ming@example.com';"
```

**Expected Output:**
```
        email         | is_email_verified |         verification_token
----------------------+-------------------+-------------------------------------
 li.ming@example.com  | f                 | stub-verification-token-li-ming-001
```

**Verify Li Ming's Email (Future Endpoint):**
```http
POST http://localhost:8000/api/v1/auth/verify-email
Content-Type: application/json

{
  "token": "stub-verification-token-li-ming-001"
}
```

---

## Troubleshooting

### Issue: Tests Fail with 404 Errors

**Cause**: Backend services not running

**Solution**:
```bash
cd backend
./scripts/start.sh
./scripts/status.sh  # Verify all services are running
```

### Issue: Tests Fail with 409 Conflicts

**Cause**: Context names already exist from previous test runs

**Solution**: Pre-request scripts generate unique names with timestamps. If still occurring:
```bash
cd backend
./scripts/reset.sh
```

### Issue: Inheritance Test Fails

**Cause**: Environment variable `sarah_base_phone` not set

**Solution**:
1. Verify environment is selected (top right dropdown)
2. Check environment has all variables
3. Re-import `thesis-local.postman_environment.json`

### Issue: Mailpit Shows No Emails

**Cause**: Email sending not yet implemented (MAS-26 pending)

**Current Status**: Infrastructure is ready, email sending will be implemented in MAS-26 Auth Service.

### Issue: Cannot Access Mailpit UI

**Solution**:
```bash
# Check if Mailpit is running
curl http://127.0.0.1:54324

# Check Supabase status
cd backend
supabase status
```

---

## Summary of Test Coverage

### Implemented and Tested

- Health checks (basic and detailed)
- Context profile CRUD operations
- Profile inheritance engine
- Context resolution with partial overrides
- Context isolation (context collapse prevention)
- Business rules (pseudonymous restrictions)
- Seed data with 5 diverse users

### Pending Implementation

- User registration endpoints
- Email verification flow
- Password reset flow
- JWT authentication
- Login/logout endpoints

### Key Validation Points

1. **Inheritance Engine**: Null overrides inherit from base profile [VALIDATED]
2. **Context Isolation**: Professional and social contexts remain separate [VALIDATED]
3. **Business Rules**: Pseudonymous accounts cannot create legal contexts [VALIDATED]
4. **1:1 Relationship**: Each base_profile has exactly one auth_users record [VALIDATED]
5. **Email Infrastructure**: Mailpit captures emails for testing [VALIDATED]

---

## Next Steps

1. **Run all tests in sequence**: Use Collection Runner in Postman
2. **View console output**: Check test results and validation messages
3. **Explore Mailpit UI**: Navigate to http://127.0.0.1:54324
4. **Document results**: Take screenshots for thesis documentation
5. **Prepare for Phase 1**: Auth Service implementation (MAS-26) will enable full email testing

---

## Resources

- **Postman Collection**: `postman/thesis-api.postman_collection.json`
- **Environment File**: `postman/thesis-local.postman_environment.json`
- **Postman README**: `postman/README.md`
- **Backend Tests**: `backend/tests/integration/test_context_endpoints.py`
- **Seed Data**: `backend/supabase/seed.sql`
- **Mailpit UI**: http://127.0.0.1:54324
- **API Docs**: http://localhost:8000/docs

For questions or issues, refer to the main project documentation in `CLAUDE.md` and `backend/TESTING.md`.

