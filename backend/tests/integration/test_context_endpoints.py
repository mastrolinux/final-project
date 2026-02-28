"""Integration tests for context profile endpoints."""

from datetime import UTC

from fastapi.testclient import TestClient

from src.models.profile import BaseProfile, IdentityName


class TestCreateContextProfile:
    """Test POST /profiles/{user_id}/contexts"""

    def test_create_context_success(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test successful context creation"""
        response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "LinkedIn",
                "display_name_override": "Dr. Sarah Chen, MD",
                "email_override": "work@hospital.org",
                "bio": "Psychiatrist specializing in trauma",
            },
            headers={"Authorization": f"Bearer {verified_token}"},
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
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test creating context with only required fields"""
        response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Personal"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["context_type"] == "social"
        assert data["context_name"] == "Personal"
        assert data["display_name_override"] is None
        assert data["email_override"] is None

    def test_create_context_for_nonexistent_user(self, client: TestClient, verified_token: str):
        """Test creating context for non-existent user returns 404"""
        response = client.post(
            "/api/v1/profiles/00000000-0000-0000-0000-000000000999/contexts",
            json={"context_type": "professional", "context_name": "Work"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )

        assert response.status_code == 404

    def test_create_duplicate_context_fails(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test creating duplicate context returns 409"""
        headers = {"Authorization": f"Bearer {verified_token}"}
        client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "LinkedIn"},
            headers=headers,
        )

        response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "LinkedIn"},
            headers=headers,
        )

        assert response.status_code == 409

    def test_pseudonymous_cannot_create_legal_context(
        self,
        client: TestClient,
        sample_pseudonymous_profile: BaseProfile,
        pseudonymous_token: str,
    ):
        """Test pseudonymous account cannot create legal context"""
        response = client.post(
            f"/api/v1/profiles/{sample_pseudonymous_profile.user_id}/contexts",
            json={"context_type": "legal", "context_name": "Government"},
            headers={"Authorization": f"Bearer {pseudonymous_token}"},
        )

        assert response.status_code == 403

    def test_create_context_without_auth_returns_401(
        self, client: TestClient, sample_verified_profile: BaseProfile
    ):
        """Test creating context without JWT returns 401"""
        response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Personal"},
        )

        assert response.status_code == 401


class TestListUserContexts:
    """Test GET /profiles/{user_id}/contexts"""

    def test_list_contexts_empty(self, client: TestClient, sample_verified_profile: BaseProfile):
        """Test listing contexts for user with no contexts"""
        response = client.get(f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_contexts_multiple(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test listing multiple contexts"""
        headers = {"Authorization": f"Bearer {verified_token}"}
        client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "LinkedIn"},
            headers=headers,
        )
        client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Facebook"},
            headers=headers,
        )

        response = client.get(f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts")

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
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test successfully retrieving a context"""
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work",
                "display_name_override": "Dr. Sarah Chen",
            },
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        context_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == context_id
        assert data["context_name"] == "Work"
        assert data["display_name_override"] == "Dr. Sarah Chen"

    def test_get_nonexistent_context(
        self, client: TestClient, sample_verified_profile: BaseProfile
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
        sample_unverified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test accessing context belonging to different user returns 403"""
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "Work"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        context_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_unverified_profile.user_id}/contexts/{context_id}"
        )

        assert response.status_code == 403


class TestGetResolvedContextProfile:
    """Test GET /profiles/{user_id}/contexts/{context_id}/resolved"""

    def test_resolve_context_with_full_overrides(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName,
        verified_token: str,
    ):
        """Test resolving context with all overrides applied"""
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work",
                "display_name_override": "Dr. Sarah Chen",
                "email_override": "work@hospital.org",
                "phone_override": "+1-555-9999",
                "bio": "Professional bio",
            },
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        context_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["display_name"] == "Dr. Sarah Chen"
        assert data["email"] == "work@hospital.org"
        assert data["phone"] == "+1-555-9999"
        assert data["bio"] == "Professional bio"

        assert data["account_type"] == "verified"
        assert data["preferred_language"] == "en"

        assert data["context_type"] == "professional"
        assert data["context_name"] == "Work"

        assert len(data["identity_names"]) > 0

    def test_resolve_context_with_partial_overrides(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test resolving context with partial overrides inherits from base."""
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work",
                "email_override": "work@company.com",
            },
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        context_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == "work@company.com"
        assert data["phone"] == sample_verified_profile.primary_phone
        assert data["display_name"] is None

    def test_resolve_context_with_no_overrides(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test resolving context with no overrides returns base values."""
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Personal"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        context_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )

        assert response.status_code == 200
        data = response.json()

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
        sample_identity_name: IdentityName,
    ):
        """Test resolving base profile without context"""
        response = client.get(f"/api/v1/profiles/{sample_verified_profile.user_id}/resolved")

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == sample_verified_profile.primary_email
        assert data["phone"] == sample_verified_profile.primary_phone
        assert data["preferred_language"] == "en"

        assert data["context_type"] is None
        assert data["context_name"] is None
        assert data["display_name"] is None
        assert data["bio"] is None

        assert len(data["identity_names"]) > 0


class TestUpdateContextProfile:
    """Test PATCH /profiles/{user_id}/contexts/{context_id}"""

    def test_update_context_success(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test successfully updating a context"""
        headers = {"Authorization": f"Bearer {verified_token}"}
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "Work", "bio": "Old bio"},
            headers=headers,
        )
        context_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}",
            json={"bio": "New bio", "email_override": "newemail@work.com"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "New bio"
        assert data["email_override"] == "newemail@work.com"

    def test_update_nonexistent_context(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test updating non-existent context returns 404"""
        response = client.patch(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/00000000-0000-0000-0000-000000000999",
            json={"bio": "New bio"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )

        assert response.status_code == 404

    def test_clear_override_by_setting_null(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """
        Test clearing an override by explicitly setting it to null.

        This tests the sentinel value pattern: setting a field to null should
        clear the override (allowing inheritance from base profile), while
        omitting the field should keep the existing value.
        """
        headers = {"Authorization": f"Bearer {verified_token}"}
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "healthcare",
                "context_name": "Hospital",
                "phone_override": "+1-555-0100",
                "email_override": "hospital@example.com",
                "bio": "Medical professional",
            },
            headers=headers,
        )
        assert create_response.status_code == 201
        context_id = create_response.json()["id"]

        get_response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}"
        )
        assert get_response.json()["phone_override"] == "+1-555-0100"
        assert get_response.json()["email_override"] == "hospital@example.com"
        assert get_response.json()["bio"] == "Medical professional"

        update_response = client.patch(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}",
            json={"phone_override": None, "bio": "Updated bio"},
            headers=headers,
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["phone_override"] is None
        assert data["email_override"] == "hospital@example.com"
        assert data["bio"] == "Updated bio"

        resolved_response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )
        assert resolved_response.status_code == 200
        resolved_data = resolved_response.json()
        assert resolved_data["phone"] == sample_verified_profile.primary_phone
        assert resolved_data["email"] == "hospital@example.com"


class TestDeleteContextProfile:
    """Test DELETE /profiles/{user_id}/contexts/{context_id}"""

    def test_delete_context_success(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test successfully deleting a context"""
        headers = {"Authorization": f"Bearer {verified_token}"}
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Facebook"},
            headers=headers,
        )
        context_id = create_response.json()["id"]

        response = client.delete(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}",
            headers=headers,
        )

        assert response.status_code == 204

        get_response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}"
        )
        assert get_response.status_code == 404

    def test_delete_nonexistent_context(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test deleting non-existent context returns 404"""
        response = client.delete(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/00000000-0000-0000-0000-000000000999",
            headers={"Authorization": f"Bearer {verified_token}"},
        )

        assert response.status_code == 404


class TestEndToEndScenario:
    """End-to-end scenario testing complete workflow"""

    def test_privacy_focused_professional_scenario(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName,
        verified_token: str,
    ):
        """Test privacy-focused psychiatrist scenario with separate contexts."""
        user_id = sample_verified_profile.user_id
        headers = {"Authorization": f"Bearer {verified_token}"}

        prof_response = client.post(
            f"/api/v1/profiles/{user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Hospital Network",
                "display_name_override": "Dr. Sarah Chen, MD, PhD",
                "email_override": "s.chen@hospital.org",
                "bio": "Board-certified psychiatrist specializing in trauma and PTSD",
            },
            headers=headers,
        )
        assert prof_response.status_code == 201
        prof_context_id = prof_response.json()["id"]

        social_response = client.post(
            f"/api/v1/profiles/{user_id}/contexts",
            json={
                "context_type": "social",
                "context_name": "Fitness App",
                "display_name_override": "Sarah",
                "bio": "Health and wellness enthusiast",
            },
            headers=headers,
        )
        assert social_response.status_code == 201
        social_context_id = social_response.json()["id"]

        prof_resolved = client.get(
            f"/api/v1/profiles/{user_id}/contexts/{prof_context_id}/resolved"
        ).json()

        assert prof_resolved["display_name"] == "Dr. Sarah Chen, MD, PhD"
        assert prof_resolved["email"] == "s.chen@hospital.org"
        assert "psychiatrist" in prof_resolved["bio"].lower()

        social_resolved = client.get(
            f"/api/v1/profiles/{user_id}/contexts/{social_context_id}/resolved"
        ).json()

        assert social_resolved["display_name"] == "Sarah"
        assert social_resolved["email"] == sample_verified_profile.primary_email  # Inherited
        assert "wellness" in social_resolved["bio"].lower()

        assert prof_resolved["email"] != social_resolved["email"]
        assert prof_resolved["bio"] != social_resolved["bio"]


class TestAcceptLanguageHeaderParsing:
    """Test Accept-Language header parsing for multilingual name resolution"""

    def test_accept_language_header_chinese(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test Accept-Language header with Chinese locale"""
        context_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Work",
                "display_name_override": "李明工程师",
            },
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        assert context_response.status_code == 201
        context_id = context_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved",
            headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["display_name"] == "李明工程师"

    def test_accept_language_header_english(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test Accept-Language header with English locale"""
        context_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "social",
                "context_name": "Friends",
                "display_name_override": "Mike",
            },
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        assert context_response.status_code == 201
        context_id = context_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved",
            headers={"Accept-Language": "en-US,en;q=0.9"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Mike"

    def test_accept_language_header_missing_defaults_to_english(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test missing Accept-Language header defaults to English"""
        context_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "Default"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        assert context_response.status_code == 201
        context_id = context_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )

        assert response.status_code == 200

    def test_accept_language_complex_header(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test complex Accept-Language header with quality values"""
        context_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "International"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        assert context_response.status_code == 201
        context_id = context_response.json()["id"]

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved",
            headers={"Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,*;q=0.5"},
        )

        assert response.status_code == 200


class TestTemporalValidityIntegration:
    """Test temporal validity checking at API level"""

    def test_resolve_expired_context_returns_410(
        self,
        client: TestClient,
        db_session,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test expired context returns HTTP 410 Gone"""
        from datetime import datetime, timedelta

        from sqlalchemy import text

        context_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={
                "context_type": "professional",
                "context_name": "Old Job",
                "display_name_override": "Former Title",
            },
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        assert context_response.status_code == 201
        context_id = context_response.json()["id"]

        past_date = datetime.now(UTC) - timedelta(days=1)
        db_session.execute(
            text("UPDATE context_profiles SET valid_to = :valid_to WHERE id = :id"),
            {"valid_to": past_date, "id": context_id},
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )

        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()

    def test_resolve_future_valid_context_succeeds(
        self,
        client: TestClient,
        db_session,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """Test context with future valid_to resolves successfully"""
        from datetime import datetime, timedelta

        from sqlalchemy import text

        context_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "professional", "context_name": "Current Job"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        assert context_response.status_code == 201
        context_id = context_response.json()["id"]

        future_date = datetime.now(UTC) + timedelta(days=365)
        db_session.execute(
            text("UPDATE context_profiles SET valid_to = :valid_to WHERE id = :id"),
            {"valid_to": future_date, "id": context_id},
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )

        assert response.status_code == 200


class TestEmailVerificationEnforcement:
    """Test that write endpoints reject requests from unverified-email users."""

    def test_create_context_with_unverified_email_returns_403(
        self,
        client: TestClient,
        sample_unverified_profile: BaseProfile,
        unverified_email_token: str,
    ):
        """Unverified-email user cannot create context profiles."""
        response = client.post(
            f"/api/v1/profiles/{sample_unverified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Personal"},
            headers={"Authorization": f"Bearer {unverified_email_token}"},
        )

        assert response.status_code == 403
        assert "email verification required" in response.json()["detail"].lower()

    def test_update_context_with_unverified_email_returns_403(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        sample_unverified_profile: BaseProfile,
        verified_token: str,
        unverified_email_token: str,
    ):
        """Unverified-email user cannot update context profiles."""
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Test"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        context_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}",
            json={"bio": "Updated"},
            headers={"Authorization": f"Bearer {unverified_email_token}"},
        )

        assert response.status_code == 403
        assert "email verification required" in response.json()["detail"].lower()

    def test_delete_context_with_unverified_email_returns_403(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        sample_unverified_profile: BaseProfile,
        verified_token: str,
        unverified_email_token: str,
    ):
        """Unverified-email user cannot delete context profiles."""
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "ToDelete"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        context_id = create_response.json()["id"]

        response = client.delete(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}",
            headers={"Authorization": f"Bearer {unverified_email_token}"},
        )

        assert response.status_code == 403
        assert "email verification required" in response.json()["detail"].lower()

    def test_read_endpoints_still_work_without_auth(
        self,
        client: TestClient,
        sample_verified_profile: BaseProfile,
        verified_token: str,
    ):
        """GET endpoints remain accessible without JWT authentication."""
        create_response = client.post(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts",
            json={"context_type": "social", "context_name": "Public"},
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        context_id = create_response.json()["id"]

        list_response = client.get(f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts")
        assert list_response.status_code == 200

        get_response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}"
        )
        assert get_response.status_code == 200

        resolved_response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/contexts/{context_id}/resolved"
        )
        assert resolved_response.status_code == 200

        base_resolved_response = client.get(
            f"/api/v1/profiles/{sample_verified_profile.user_id}/resolved"
        )
        assert base_resolved_response.status_code == 200
