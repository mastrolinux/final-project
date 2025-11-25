"""
Integration Tests for API Endpoints

Tests API endpoints with real database interactions.
"""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns correct response"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Identity and Profile Management API"
    assert data["version"] == "1.0.0"
    assert "/docs" in data["docs"]


def test_health_endpoint(client: TestClient):
    """Test basic health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Identity and Profile Management API"
    assert data["version"] == "1.0.0"


def test_detailed_health_endpoint(client: TestClient):
    """Test detailed health check endpoint"""
    response = client.get("/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "supabase" in data["components"]
    assert "tables" in data["components"]
    
    # Database component should have status
    db_component = data["components"]["database"]
    assert "status" in db_component
    assert "message" in db_component


def test_api_v1_health_endpoint(client: TestClient):
    """Test API v1 health endpoint"""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "v1"


def test_database_test_endpoint_empty_database(client: TestClient):
    """Test database test endpoint with empty database"""
    response = client.get("/api/v1/database/test")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Database connection successful"
    assert data["data"]["profile_count"] == 0
    assert data["data"]["name_count"] == 0


def test_database_test_endpoint_with_data(client: TestClient, sample_profiles_with_names):
    """Test database test endpoint with sample data"""
    response = client.get("/api/v1/database/test")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["profile_count"] == 3  
    assert len(data["data"]["sample_profiles"]) <= 5  # Max 5 samples


def test_profile_counts_endpoint_empty(client: TestClient):
    """Test profile counts endpoint with empty database"""
    response = client.get("/api/v1/database/profiles/count")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["total"] == 0


def test_profile_counts_endpoint_with_data(client: TestClient, sample_profiles_with_names):
    """Test profile counts endpoint with sample data"""
    response = client.get("/api/v1/database/profiles/count")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["total"] == 3  
    assert "by_type" in data["data"]


def test_get_profile_by_id(client: TestClient, sample_verified_profile, sample_identity_name):
    """Test getting a specific profile by ID"""
    user_id = str(sample_verified_profile.user_id)
    response = client.get(f"/api/v1/database/profiles/{user_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["profile"]["user_id"] == user_id
    assert data["data"]["profile"]["account_type"] == "verified"
    assert len(data["data"]["names"]) >= 1


def test_get_nonexistent_profile(client: TestClient):
    """Test getting a nonexistent profile returns 404"""
    fake_uuid = "00000000-0000-0000-0000-000000000999"
    response = client.get(f"/api/v1/database/profiles/{fake_uuid}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_openapi_docs_accessible(client: TestClient):
    """Test that OpenAPI documentation is accessible"""
    response = client.get("/docs")
    
    assert response.status_code == 200


def test_openapi_json_accessible(client: TestClient):
    """Test that OpenAPI JSON schema is accessible"""
    response = client.get("/openapi.json")
    
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data

