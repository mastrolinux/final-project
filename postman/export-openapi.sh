#!/bin/bash
# Export OpenAPI specification from running FastAPI server
# This script should be run when the backend is running

set -e

echo "======================================"
echo "Export OpenAPI Specification"
echo "======================================"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend is not running!"
    echo ""
    echo "Please start the backend first:"
    echo "  cd backend"
    echo "  ./scripts/start.sh"
    echo ""
    exit 1
fi

echo "Backend is running"
echo ""

# Export OpenAPI spec
echo "Exporting OpenAPI specification..."
curl -s http://localhost:8000/openapi.json -o openapi.json

if [ $? -eq 0 ]; then
    echo "✓ OpenAPI spec exported to: postman/openapi.json"
    echo ""
    echo "Import into Postman:"
    echo "  1. Open Postman"
    echo "  2. Click 'Import' (top left)"
    echo "  3. Select 'Link' tab"
    echo "  4. Paste: http://localhost:8000/openapi.json"
    echo "  5. Click 'Continue' and 'Import'"
    echo ""
    echo "Or use the file:"
    echo "  Import → File → Select postman/openapi.json"
    echo ""
else
    echo "Failed to export OpenAPI spec"
    exit 1
fi
