# Postman Integration Tests

This directory contains Postman collections and environments for testing the Identity and Profile Management API. The collections mirror the pytest integration tests in `backend/tests/integration/test_context_endpoints.py`.

## Quick Start

### 1. Import Environment

1. Open Postman
2. Click "Environments" (left sidebar)
3. Click "Import"
4. Select `thesis-local.postman_environment.json`
5. Select the "Thesis - Local Development" environment from the dropdown (top right)

### 2. Import Collection

1. Click "Import" button (top left)
2. Select `thesis-api.postman_collection.json`
3. The collection "Identity and Profile Management API" will appear in your Collections

### 3. Start Backend Services

Before running any requests, ensure the backend is running:

```bash
cd backend
./scripts/start.sh
```

Verify the API is accessible:
```bash
curl http://localhost:8000/health
```

### 4. Run the Collection

**Option A: Manual Execution**

1. Open the collection
2. Navigate through folders to explore endpoints
3. Run individual requests or use "Run Collection" for batch execution

**Option B: Collection Runner**

1. Click "Runner" button (top left)
2. Select "Identity and Profile Management API"
3. Select "Thesis - Local Development" environment
4. Click "Run Identity and Profile Management API"
5. View test results with pass/fail status

**Option C: Command Line (Newman)**

```bash
# Install Newman (Postman CLI)
npm install -g newman

# Run the collection
newman run thesis-api.postman_collection.json \
  -e thesis-local.postman_environment.json \
  --bail \
  --color on
```

## Collection Structure

The collection is organized to mirror the pytest test classes:

```
Identity Management API
├── 01 - Health Checks
│   ├── GET /health
│   └── GET /health/detailed
├── 02 - Create Context Profile
│   ├── Create Professional Context (Success)
│   ├── Create Social Context (Minimal Fields)
│   ├── Create for Nonexistent User (404)
│   └── Pseudonymous Cannot Create Legal (403)
├── 03 - List User Contexts
│   └── List User Contexts
├── 04 - Get Resolved Profile (CRITICAL)
│   ├── Resolve Context with Full Overrides
│   ├── Resolve with Partial Overrides (Inheritance Test)
│   ├── Get Resolved Partial Context (Validates Inheritance)
│   └── Resolve Base Profile (No Context)
├── 05 - Update Context Profile
│   └── Update Context Success
├── 06 - Delete Context Profile
│   └── Delete Context Success
└── 07 - End-to-End Scenarios
    ├── Step 1: Create Professional Context
    ├── Step 2: Create Social Context
    ├── Step 3: Resolve Professional Context
    ├── Step 4: Resolve Social Context
    └── Step 5: Validate Context Isolation
```

## Key Features

### Pre-Request Scripts

Requests that create resources include pre-request scripts to generate unique identifiers:

```javascript
// Generate unique context name to prevent 409 conflicts
const timestamp = Date.now();
const contextName = `Test-Professional-${timestamp}`;
pm.collectionVariables.set("context_name", contextName);
```

This ensures tests can be run multiple times without conflicts.

### Test Scripts

Each request includes test scripts that mirror the pytest assertions:

```javascript
pm.test("Status code is 201 Created", function () {
    pm.response.to.have.status(201);
});

pm.test("Response has context data", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("context_type");
    pm.expect(jsonData.context_type).to.eql("professional");
});
```

### Environment Variables

The environment file includes:

- **Base Configuration**: `base_url`, `api_version`
- **Seed Data UUIDs**: `sarah_user_id`, `li_ming_user_id`, etc. (from `backend/supabase/seed.sql`)
- **Base Profile Data**: `sarah_base_email`, `sarah_base_phone` (for inheritance tests)
- **Dynamic Variables**: Set by requests and used in subsequent requests

## Critical Tests

### Inheritance Engine Validation

The most important test validates the inheritance engine:

**Folder**: `04 - Get Resolved Profile (CRITICAL)`  
**Request**: `Get Resolved Partial Context (Validates Inheritance)`

This test:
1. Creates a context with only email override
2. Retrieves the resolved profile
3. Verifies email is overridden
4. **Verifies phone is inherited from base profile** (validates inheritance!)

```javascript
pm.test("Phone is inherited from base profile", function () {
    const jsonData = pm.response.json();
    const basePhone = pm.environment.get("sarah_base_phone");
    
    // This validates the inheritance engine!
    pm.expect(jsonData.phone).to.eql(basePhone);
    
    console.log("✓ Inheritance verified: phone inherited from base");
});
```

### End-to-End Scenario

**Folder**: `07 - End-to-End Scenarios`

This scenario demonstrates the complete use case from the preliminary report:

1. **Create Professional Context**: Dr. Sarah Chen with work credentials
2. **Create Social Context**: Sarah with personal info
3. **Resolve Professional Context**: Get what hospital network sees
4. **Resolve Social Context**: Get what fitness app sees
5. **Validate Context Isolation**: Verify contexts don't leak information

The final validation confirms:
- Professional and social contexts use different emails
- Professional credentials (psychiatrist, MD) are hidden from social context
- Personal wellness info is hidden from professional context

This proves **context collapse prevention** - the core contribution of the thesis.

## Exporting OpenAPI Spec (Optional)

If you want to regenerate the collection from the live API:

1. Ensure backend is running
2. Export the OpenAPI spec:
   ```bash
   curl http://localhost:8000/openapi.json -o postman/openapi.json
   ```
3. In Postman: Import → Link → `http://localhost:8000/openapi.json`

Note: The current collection was manually crafted to include comprehensive test scripts. Auto-imported collections will need test scripts added.

## Comparison: pytest vs Postman

| Aspect | pytest Integration Tests | Postman Collection |
|--------|--------------------------|---------------------|
| **Purpose** | Automated testing in CI/CD | Manual testing, demonstrations, API docs |
| **Test Data** | Fixtures in `conftest.py` | Environment variables + pre-request scripts |
| **Assertions** | Python `assert` statements | JavaScript `pm.test()` and `pm.expect()` |
| **Setup/Teardown** | pytest fixtures | Pre-request and test scripts |
| **Sequential Tests** | Independent test functions | Folder ordering + saved variables |
| **Best For** | Development, TDD, CI/CD | Exploration, debugging, stakeholder demos |

## Recommended Workflow

### For Development
1. Run pytest for comprehensive automated testing
2. Use Postman for manual exploration and debugging specific endpoints

### For Demonstrations
1. Use Postman to show the API in action to your thesis supervisor or examiners
2. Run the "Privacy-Focused Professional" end-to-end scenario
3. Show the inheritance engine working via the `/resolved` endpoint
4. Highlight the console output showing context isolation

### For Documentation
1. Export Postman collection with request/response examples
2. Share with stakeholders as interactive API documentation
3. Use Postman's "Publish Documentation" feature for web-based docs

## Troubleshooting

### Tests Fail with 404 Errors

**Problem**: Backend services not running  
**Solution**: 
```bash
cd backend
./scripts/start.sh
./scripts/status.sh  # Verify services are running
```

### Tests Fail with 409 Conflicts

**Problem**: Context names already exist  
**Solution**: Pre-request scripts generate unique names with timestamps. If still occurring, reset the database:
```bash
cd backend
./scripts/reset.sh
```

### Inheritance Test Fails

**Problem**: Environment variable `sarah_base_phone` not set  
**Solution**: Verify the environment is selected (top right dropdown) and contains all required variables. Re-import the environment file if needed.

### Collection Variables Not Saved

**Problem**: Running requests out of order  
**Solution**: For sequential tests (especially in folder 07), use "Run Collection" to execute in order. Individual requests may fail if they depend on previous requests.

## Files

- **`thesis-api.postman_collection.json`**: Main collection with all test scenarios
- **`thesis-local.postman_environment.json`**: Local development environment with seed data
- **`openapi.json`**: (Generated) OpenAPI specification from FastAPI
- **`README.md`**: This file

## Integration with CI/CD

To run Postman tests in your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Run Postman Tests
  run: |
    npm install -g newman
    newman run postman/thesis-api.postman_collection.json \
      -e postman/thesis-local.postman_environment.json \
      --reporters cli,json \
      --reporter-json-export test-results/newman-results.json
```

## Version Control

Both collection and environment files are version controlled. When making changes:

1. Edit in Postman
2. Export updated files (Collection v2.1 format)
3. Overwrite existing files
4. Commit changes:
   ```bash
   git add postman/
   git commit -m "Update Postman collection: add new test scenarios"
   ```

## Further Reading

- [Postman Documentation](https://learning.postman.com/docs/getting-started/introduction/)
- [Writing Tests in Postman](https://learning.postman.com/docs/writing-scripts/test-scripts/)
- [Newman CLI Documentation](https://learning.postman.com/docs/running-collections/using-newman-cli/command-line-integration-with-newman/)
- [Backend Testing Guide](../backend/TESTING.md)

## Support

For issues or questions:
1. Check backend logs: `cd backend && docker compose logs -f api`
2. Verify database health: `curl http://localhost:8000/health/detailed`
3. Review pytest tests for comparison: `backend/tests/integration/test_context_endpoints.py`
