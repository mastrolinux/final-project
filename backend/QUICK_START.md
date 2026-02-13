# Quick Start Guide - Identity API Backend

## System Status

Your backend is fully operational. 

### What's Working

- Supabase PostgreSQL: Running with migrations applied
- FastAPI Application: Running on http://localhost:8000
- Database Tables: `base_profiles` and `identity_names` created
- Seed Data: 5 sample profiles loaded
- Tests: 255+ tests passing
- API Endpoints: All endpoints functional

### Minor Issue (Non-blocking)

- Supabase Client Library: Version compatibility with `proxy` argument
  - **Impact**: Minor - doesn't affect core functionality
  - **Why**: Using SQLAlchemy for database access (which works perfectly)
  - **Fix**: Can be ignored or fixed by updating Supabase client later

## Try It Now

### 1. Check System Health

```bash
curl http://localhost:8000/health/detailed | jq
```

**Expected:**
- Database: healthy
- Tables: healthy
- Overall: degraded (due to Supabase client, but functional)

### 2. View Seed Data

```bash
# Get all profiles
curl http://localhost:8000/api/v1/database/test | jq

# Get profile counts by type
curl http://localhost:8000/api/v1/database/profiles/count | jq
```

**You have 5 seed profiles:**
- 3 verified accounts
- 1 unverified account
- 1 pseudonymous account

### 3. Query Specific Profile

```bash
# Sarah Chen (verified, Western naming)
curl http://localhost:8000/api/v1/database/profiles/00000000-0000-0000-0000-000000000001 | jq

# Li Ming (unverified, Chinese naming)
curl http://localhost:8000/api/v1/database/profiles/00000000-0000-0000-0000-000000000002 | jq

# Alex (pseudonymous)
curl http://localhost:8000/api/v1/database/profiles/00000000-0000-0000-0000-000000000003 | jq
```

### 4. Interactive API Documentation

Open in your browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Try the endpoints directly in the browser!

### 5. Supabase Studio

Browse your database visually:
```bash
open http://127.0.0.1:54323
```

Navigate to:
- **Table Editor** → View `base_profiles` and `identity_names`
- **SQL Editor** → Run custom queries

### 6. Direct Database Access

```bash
# Query profiles
docker exec supabase_db_backend psql -U postgres -d postgres -c "
SELECT user_id, account_type, primary_email, preferred_language 
FROM base_profiles;
"

# Query multilingual names
docker exec supabase_db_backend psql -U postgres -d postgres -c "
SELECT id, name_type, name_value, is_primary, is_deprecated
FROM identity_names 
LIMIT 5;
"
```

## Running Tests

### All Tests

```bash
docker compose exec api pytest -v
```

**Current Results:**
- 255+ tests passing (unit + integration)
- OAuth, auth, context, and profile tests all passing

### Test by Category

```bash
# Unit tests (fast)
docker compose exec api pytest tests/unit/ -v

# Integration tests
docker compose exec api pytest tests/integration/ -v

# Model tests (all passing)
docker compose exec api pytest tests/unit/test_models.py -v

# Endpoint tests (all passing)
docker compose exec api pytest tests/integration/test_endpoints.py -v
```

### Test Coverage

```bash
docker compose exec api pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Sample Data Overview

Your database contains 5 diverse profiles demonstrating:

### 1. Sarah Chen (Verified)
- **Email**: sarah.chen@example.com
- **Type**: Verified account
- **Names**: Western naming convention
- **Has**: Legal name, primary email, phone

### 2. Li Ming (Unverified)
- **Email**: li.ming@example.com  
- **Type**: Unverified account
- **Names**: Chinese naming (李明) with multilingual support
- **Demonstrates**: Family-first name ordering, multiple scripts

### 3. Alex (Pseudonymous)
- **Email**: alex.anonymous@protonmail.com
- **Type**: Pseudonymous account
- **Names**: Preferred name only, no legal name
- **Demonstrates**: Privacy-first approach for vulnerable populations

### 4. Sukarno (Verified)
- **Email**: sukarno@example.id
- **Type**: Verified account
- **Names**: Mononym (single name)
- **Demonstrates**: Indonesian naming convention

### 5. Jordan Smith (Verified)
- **Email**: jordan.smith@example.com
- **Type**: Verified account with name change
- **Names**: Current name + deprecated historical name
- **Demonstrates**: Deadname handling with visibility controls

## Common Operations

### Restart Services

```bash
./scripts/stop.sh
./scripts/start.sh
```

### Reset Database (Fresh Start)

```bash
./scripts/reset.sh
```

This will:
1. Stop services
2. Drop all data
3. Reapply migrations
4. Reload seed data
5. Restart services

### View Logs

```bash
# Live logs
docker compose logs -f api

# Recent logs
./scripts/status.sh
```

### Check Status

```bash
./scripts/status.sh
```

Shows:
- Service status
- Recent logs
- Available URLs
- Helpful commands

## Admin Access Setup

To access admin features (OAuth client management), configure your email as an admin:

### Option 1: Environment Variable (Recommended for Development)

Edit `backend/.env`:
```bash
ADMIN_USER_EMAILS=your.email@example.com
```

Restart the backend:
```bash
docker compose restart api
```

### Option 2: Database Flag

```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c \
  "UPDATE auth_users SET is_admin = true WHERE email = 'your.email@example.com';"
```

### Verify Admin Status

After logging in, your `is_admin` field should be `true`:
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your.email@example.com", "password": "YourPassword123!"}' \
  | jq '.is_admin'
```

## Google OAuth Social Login Setup

The API supports social login with Google using OAuth 2.0 Authorization Code Flow with PKCE.

### Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. If prompted, configure the OAuth consent screen:
   - User Type: **External** (for testing)
   - App name: "Identity Management System" (or your choice)
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add `openid`, `email`, and `profile`
   - Test users: Add your Google account email
6. Configure the OAuth Client:
   - Application type: **Web application**
   - Name: "Identity API - Local Development"
   - Authorized redirect URIs: Add
     ```
     http://localhost:8000/api/v1/auth/social/google/callback
     ```
7. Click **Create** and note your **Client ID** and **Client Secret**

### Step 2: Configure Environment Variables

Edit `backend/.env` and add your Google OAuth credentials:

```bash
# Google OAuth 2.0 Credentials
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/social/google/callback
```

### Step 3: Reload Environment Variables

After updating `.env`, you must **recreate** the container to load the new variables:

```bash
# Option 1: Using management scripts (recommended)
./scripts/stop.sh
./scripts/start.sh

# Option 2: Force recreate the API container
docker compose up -d --force-recreate api

# Option 3: Full restart
docker compose down && docker compose up -d
```

**Note**: `docker compose restart api` does NOT reload environment variables!

### Step 4: Test Social Login

#### Option A: Using the Frontend (Recommended)

1. Start the frontend (if not running):
   ```bash
   cd ../frontend
   npm run dev
   ```

2. Navigate to http://localhost:3000/login

3. Click the **"Continue with Google"** button

4. Sign in with your Google account

5. You should be redirected back and authenticated

#### Option B: Manual API Testing

1. Get the authorization URL:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/social/google/authorize \
     -H "Content-Type: application/json" | jq
   ```

   Response:
   ```json
   {
     "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
     "state": "random-state-value",
     "code_verifier": "random-verifier-value"
   }
   ```

2. Copy the `authorization_url` and open it in a browser

3. Sign in with Google and authorize the app

4. Google will redirect to:
   ```
   http://localhost:8000/api/v1/auth/social/google/callback?code=...&state=...
   ```

5. Extract the `code` and `state` from the URL

6. Exchange the code for tokens:
   ```bash
   curl "http://localhost:8000/api/v1/auth/social/google/callback?code=YOUR_CODE&state=YOUR_STATE&code_verifier=YOUR_VERIFIER&expected_state=YOUR_STATE" | jq
   ```

   Response:
   ```json
   {
     "access_token": "eyJhbGc...",
     "refresh_token": "eyJhbGc...",
     "token_type": "bearer",
     "expires_in": 1800,
     "user_id": "uuid-here",
     "email": "your.email@gmail.com",
     "is_new_user": true
   }
   ```

### Security Features

- **PKCE (S256)**: Proof Key for Code Exchange prevents authorization code interception
- **State Parameter**: CSRF protection with random state validation
- **ID Token Verification**: Backend verifies Google's JWT signature using Google's public keys
- **Account Linking Detection**: Prevents duplicate accounts with existing email/password users

### Verify OAuth User in Database

After logging in with Google, verify the user was created:

```bash
docker exec supabase_db_backend psql -U postgres -d postgres -c "
SELECT email, provider, provider_id, is_email_verified
FROM auth_users
WHERE provider = 'google';
"
```

Expected output:
```
         email          | provider | provider_id  | is_email_verified
------------------------+----------+--------------+-------------------
 your.email@gmail.com   | google   | google-12345 | t
```

### Troubleshooting

#### Error: "OAuth credentials not configured"
- Ensure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`
- Reload environment variables (restart is not enough):
  ```bash
  ./scripts/stop.sh && ./scripts/start.sh
  # OR
  docker compose up -d --force-recreate api
  ```

#### Error: "Redirect URI mismatch"
- In Google Cloud Console, verify the redirect URI is exactly:
  ```
  http://localhost:3000/auth/social/google/callback
  ```
- HTTP (not HTTPS) for local development
- No trailing slash

#### Error: "Account linking required"
- This means the email already exists with email/password authentication
- Sign in with your password instead
- Future feature: Manual account linking will be added

#### Error: "Invalid state parameter"
- State mismatch indicates a CSRF attack or session timeout
- Try the login flow again from the beginning
- Ensure you're using the same browser session

#### Google shows "This app isn't verified"
- This is normal for apps in development mode
- Click **"Advanced"** → **"Go to [App Name] (unsafe)"**
- For production, submit your app for Google verification

### Production Setup

For production deployment, update the redirect URI in both places:

1. **Google Cloud Console**:
   ```
   https://api.yourdomain.com/api/v1/auth/social/google/callback
   ```

2. **Production Environment** (`env.production.template`):
   ```bash
   GOOGLE_REDIRECT_URI=https://api.yourdomain.com/api/v1/auth/social/google/callback
   ```

3. Submit your app for **Google OAuth Verification** to remove the "unverified app" warning

## OAuth 2.1 Quick Test

Once you have admin access, test the OAuth flow:

### 1. Create an OAuth Client

```bash
# Get admin token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "YOUR_ADMIN_EMAIL", "password": "YOUR_PASSWORD"}' \
  | jq -r '.access_token')

# Create client
curl -s -X POST http://localhost:8000/api/v1/admin/oauth/clients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "my-test-app",
    "client_name": "My Test App",
    "redirect_uris": ["http://localhost:3000/callback"],
    "allowed_scopes": ["openid", "profile:read:basic", "email"],
    "is_confidential": false,
    "token_endpoint_auth_method": "none"
  }' | jq .
```

### 2. Test Authorization Flow

See `postman/TESTING-GUIDE.md` Phase 7 for complete OAuth testing steps.

### 3. Frontend Admin UI

If running the frontend (http://localhost:3000):
1. Log in with your admin account
2. Click "Admin" in the navigation header
3. Manage OAuth clients visually

## Next Steps

Now that your backend is running, you can:

1. **Explore the API**
   - Open http://localhost:8000/docs
   - Try the endpoints interactively
   - See request/response schemas

2. **Query the Database**
   - Use Supabase Studio: http://127.0.0.1:54323
   - Run SQL queries
   - Browse table data

3. **Test OAuth Flow**
   - Create OAuth clients via admin API or UI
   - Follow the PKCE authorization flow
   - See `postman/TESTING-GUIDE.md` for detailed steps

4. **Develop New Features**
   - Add new endpoints in `src/api/v1/endpoints/`
   - Create new models in `src/models/`
   - Write tests in `tests/`

5. **Test Changes**
   ```bash
   docker compose exec api pytest -v
   ```

6. **Read Architecture Docs**
   - See `../architecture/` for detailed design
   - Understand multi-context identity
   - Learn about cultural naming patterns

## Documentation

- **Setup Guide**: `docs/SETUP.md`
- **Testing Guide**: `TESTING.md`
- **Backend README**: `README.md`
- **Architecture**: `../architecture/`
- **API Docs**: http://localhost:8000/docs

## Troubleshooting

### Database Connection Issues

```bash
# Check if Supabase is running
supabase status

# Restart if needed
supabase stop && supabase start
```

### Container Issues

```bash
# Rebuild containers
docker compose down
docker compose up -d --build

# Check logs
docker compose logs api
```

### Test Failures

```bash
# Reset database
./scripts/reset.sh

# Clear cache
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null

# Run tests
docker compose exec api pytest -v
```

## Summary

Your Identity and Profile Management API is fully functional with:

- PostgreSQL database with proper schema
- 5 diverse seed profiles demonstrating cultural inclusivity
- FastAPI with auto-generated documentation
- Comprehensive test suite (255+ tests)
- Health check endpoints
- OAuth 2.1 authorization server
- Admin interface for OAuth client management
- Supabase Studio for visual database management

Ready for development.

