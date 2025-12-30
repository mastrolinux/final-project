"""
Integration Tests for Context Profile Endpoints

End-to-end tests for context profile API endpoints.
Tests the full stack from HTTP request to database.
"""

import pytest
from fastapi.testclient import TestClient

from src.models.profile import BaseProfile, IdentityName, NameType


class TestCreateContextProfile:
    """Test POST /profiles/{user_id}/contexts"""
    
    def test_create_context_success(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test successful context creation"""
        response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "LinkedIn",
                "display_name_override": "Dr. Sarah Chen, MD",
                "email_override": "work@hospital.org",
                "bio": "Psychiatrist specializing in trauma"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["context_type"] == "professional"
        assert data["context_name"] == "LinkedIn"
        assert data["display_name_override"] == "Dr. Sarah Chen, MD"
        assert data["email_override"] == "work@hospital.org"
        assert data["bio"] == "Psychiatrist specializing in trauma"
        assert data["is_active"] is True
        assert "id" in data
    
    def test_create_context_minimal_fields(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test creating context with only required fields"""
        response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "social",
                "context_name": "Personal"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["context_type"] == "social"
        assert data["context_name"] == "Personal"
        assert data["display_name_override"] is None
        assert data["email_override"] is None
    
    def test_create_context_for_nonexistent_user(self, client: TestClient):
        """Test creating context for non-existent user returns 404"""
        response = client.post(
            "/api/v1/profiles/00000000-0000-0000-0000-000000000999/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work"
            }
        )
        
        assert response.status_code == 404
    
    def test_create_duplicate_context_fails(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test creating duplicate context returns 409"""
        # Create first context
        client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "LinkedIn"
            }
        )
        
        # Try to create duplicate
        response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "LinkedIn"
            }
        )
        
        assert response.status_code == 409
    
    def test_pseudonymous_cannot_create_legal_context(
        self,
        client: TestClient,
        sample_pseudonymous_profile: BaseProfile
    ):
        """Test pseudonymous account cannot create legal context"""
        response = client.post(
            f"/api/v1/profiles/{sample_pseudonymous_profile.user_id}/contexts",
            json={
                "context_type": "legal",
                "context_name": "Government"
            }
        )
        
        assert response.status_code == 403


class TestListUserContexts:
    """Test GET /profiles/{user_id}/contexts"""
    
    def test_list_contexts_empty(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test listing contexts for user with no contexts"""
        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts"
        )
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_contexts_multiple(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test listing multiple contexts"""
        # Create contexts
        client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "LinkedIn"}
        )
        client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Facebook"}
        )
        
        # List contexts
        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        context_names = [ctx["context_name"] for ctx in data]
        assert "LinkedIn" in context_names
        assert "Facebook" in context_names


class TestGetContextProfile:
    """Test GET /profiles/{user_id}/contexts/{context_id}"""
    
    def test_get_context_success(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test successfully retrieving a context"""
        # Create context
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work",
                "display_name_override": "Dr. Sarah Chen"
            }
        )
        context_id = create_response.json()["id"]
        
        # Get context
        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == context_id
        assert data["context_name"] == "Work"
        assert data["display_name_override"] == "Dr. Sarah Chen"
    
    def test_get_nonexistent_context(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test getting non-existent context returns 404"""
        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/00000000-0000-0000-0000-000000000999"
        )
        
        assert response.status_code == 404
    
    def test_get_context_wrong_user(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        sample_unverified_profile: BaseProfile
    ):
        """Test accessing context belonging to different user returns 403"""
        # Create context for user 1
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "Work"}
        )
        context_id = create_response.json()["id"]
        
        # Try to access as user 2
        response = client.get(
            f"/api/v1/profiles/{sample_unverified_profile.user_id}/contexts/{context_id}"
        )
        
        assert response.status_code == 403


class TestGetResolvedContextProfile:
    """
    Test GET /profiles/{user_id}/contexts/{context_id}/resolved
    
    CRITICAL ENDPOINT: Tests the inheritance engine
    """
    
    def test_resolve_context_with_full_overrides(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """Test resolving context with all overrides applied"""
        # Create context with full overrides
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work",
                "display_name_override": "Dr. Sarah Chen",
                "email_override": "work@hospital.org",
                "phone_override": "+1-555-9999",
                "bio": "Professional bio"
            }
        )
        context_id = create_response.json()["id"]
        
        # Get resolved profile
        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Overrides should be applied
        assert data["display_name"] == "Dr. Sarah Chen"
        assert data["email"] == "work@hospital.org"
        assert data["phone"] == "+1-555-9999"
        assert data["bio"] == "Professional bio"
        
        # Base profile fields preserved
        assert data["account_type"] == "verified"
        assert data["preferred_language"] == "en"
        
        # Context metadata included
        assert data["context_type"] == "professional"
        assert data["context_name"] == "Work"
        
        # Identity names included
        assert len(data["identity_names"]) > 0
    
    def test_resolve_context_with_partial_overrides(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """
        Test resolving context with partial overrides
        
        CRITICAL: Null overrides should inherit from base
        """
        # Create context with only email override
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work",
                "email_override": "work@company.com"
            }
        )
        context_id = create_response.json()["id"]
        
        # Get resolved profile
        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Email overridden
        assert data["email"] == "work@company.com"
        
        # Phone inherited from base
        assert data["phone"] == sample_verified_profile.primary_phone
        
        # Display name not overridden
        assert data["display_name"] is None
    
    def test_resolve_context_with_no_overrides(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test resolving context with no overrides returns base values"""
        # Create context with no overrides
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "social",
                "context_name": "Personal"
            }
        )
        context_id = create_response.json()["id"]
        
        # Get resolved profile
        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All values from base profile
        assert data["email"] == sample_verified_profile.primary_email
        assert data["phone"] == sample_verified_profile.primary_phone
        assert data["display_name"] is None
        assert data["bio"] is None


class TestGetResolvedBaseProfile:
    """Test GET /profiles/{user_id}/resolved"""
    
    def test_resolve_base_profile(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """Test resolving base profile without context"""
        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/resolved"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Base profile values
        assert data["email"] == sample_verified_profile.primary_email
        assert data["phone"] == sample_verified_profile.primary_phone
        assert data["preferred_language"] == "en"
        
        # No context
        assert data["context_type"] is None
        assert data["context_name"] is None
        assert data["display_name"] is None
        assert data["bio"] is None
        
        # Identity names included
        assert len(data["identity_names"]) > 0


class TestUpdateContextProfile:
    """Test PATCH /profiles/{user_id}/contexts/{context_id}"""
    
    def test_update_context_success(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test successfully updating a context"""
        # Create context
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work",
                "bio": "Old bio"
            }
        )
        context_id = create_response.json()["id"]
        
        # Update context
        response = client.patch(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}",
            json={
                "bio": "New bio",
                "email_override": "newemail@work.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "New bio"
        assert data["email_override"] == "newemail@work.com"
    
    def test_update_nonexistent_context(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test updating non-existent context returns 404"""
        response = client.patch(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/00000000-0000-0000-0000-000000000999",
            json={"bio": "New bio"}
        )
        
        assert response.status_code == 404


class TestDeleteContextProfile:
    """Test DELETE /profiles/{user_id}/contexts/{context_id}"""
    
    def test_delete_context_success(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test successfully deleting a context"""
        # Create context
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Facebook"}
        )
        context_id = create_response.json()["id"]
        
        # Delete context
        response = client.delete(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}"
        )
        
        assert response.status_code == 204
        
        # Context should no longer be retrievable
        get_response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}"
        )
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_context(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile
    ):
        """Test deleting non-existent context returns 404"""
        response = client.delete(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/00000000-0000-0000-0000-000000000999"
        )
        
        assert response.status_code == 404


class TestEndToEndScenario:
    """End-to-end scenario testing complete workflow"""
    
    def test_privacy_focused_professional_scenario(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """
        Test the user story from the design document:
        Privacy-focused psychiatrist with different contexts
        
        Demonstrates the value of context-dependent identity
        """
        user_id = sample_verified_profile.user_id
        
        # Step 1: Create professional context for work
        prof_response = client.post(
            f"/api/v1/profiles/{user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Hospital Network",
                "display_name_override": "Dr. Sarah Chen, MD, PhD",
                "email_override": "s.chen@hospital.org",
                "bio": "Board-certified psychiatrist specializing in trauma and PTSD"
            }
        )
        assert prof_response.status_code == 201
        prof_context_id = prof_response.json()["id"]
        
        # Step 2: Create social context for personal apps
        social_response = client.post(
            f"/api/v1/profiles/{user_id}/contexts",
            json={
                "context_type": "social",
                "context_name": "Fitness App",
                "display_name_override": "Sarah",
                "bio": "Health and wellness enthusiast"
            }
        )
        assert social_response.status_code == 201
        social_context_id = social_response.json()["id"]
        
        # Step 3: Resolve professional context (what hospital sees)
        prof_resolved = client.get(
            f"/api/v1/profiles/{user_id}/contexts/{prof_context_id}/resolved"
        ).json()
        
        assert prof_resolved["display_name"] == "Dr. Sarah Chen, MD, PhD"
        assert prof_resolved["email"] == "s.chen@hospital.org"
        assert "psychiatrist" in prof_resolved["bio"].lower()
        
        # Step 4: Resolve social context (what fitness app sees)
        social_resolved = client.get(
            f"/api/v1/profiles/{user_id}/contexts/{social_context_id}/resolved"
        ).json()
        
        assert social_resolved["display_name"] == "Sarah"
        assert social_resolved["email"] == sample_verified_profile.primary_email  # Inherited
        assert "wellness" in social_resolved["bio"].lower()
        
        # Step 5: Verify contexts are isolated
        assert prof_resolved["email"] != social_resolved["email"]
        assert prof_resolved["bio"] != social_resolved["bio"]
        
        # This demonstrates context collapse prevention:
        # Professional credentials hidden from fitness app
        # Personal wellness info hidden from hospital network







