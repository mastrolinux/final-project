"""
Database Test Endpoints

Provides endpoints for testing database connectivity and querying sample data.
Useful for development, testing, and debugging.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.profile import BaseProfile, IdentityName

router = APIRouter()


@router.get("/test", response_model=dict[str, Any])
def test_database_connection(db: Session = Depends(get_db)):
    """Test database connection and return sample profile data."""
    try:
        profile_count = (
            db.query(func.count(BaseProfile.user_id))
            .filter(BaseProfile.deleted_at.is_(None))
            .scalar()
        )

        name_count = db.query(func.count(IdentityName.id)).scalar()

        sample_profiles = (
            db.query(BaseProfile).filter(BaseProfile.deleted_at.is_(None)).limit(5).all()
        )

        profiles_data = []
        for profile in sample_profiles:
            names = db.query(IdentityName).filter(IdentityName.identity_id == profile.user_id).all()

            profiles_data.append(
                {
                    "user_id": str(profile.user_id),
                    "account_type": profile.account_type.value,
                    "primary_email": profile.primary_email,
                    "preferred_language": profile.preferred_language,
                    "created_at": profile.created_at.isoformat() if profile.created_at else None,
                    "names_count": len(names),
                    "names": [
                        {
                            "type": name.name_type.value,
                            "value": name.name_value,
                            "is_primary": name.is_primary,
                        }
                        for name in names
                    ],
                }
            )

        return {
            "status": "success",
            "message": "Database connection successful",
            "data": {
                "profile_count": profile_count,
                "name_count": name_count,
                "sample_profiles": profiles_data,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Database query failed", "error": str(e)},
        )


@router.get("/profiles/count", response_model=dict[str, Any])
def get_profile_counts(db: Session = Depends(get_db)):
    """Get profile counts grouped by account type."""
    try:
        counts = (
            db.query(BaseProfile.account_type, func.count(BaseProfile.user_id).label("count"))
            .filter(BaseProfile.deleted_at.is_(None))
            .group_by(BaseProfile.account_type)
            .all()
        )

        counts_dict = {account_type.value: count for account_type, count in counts}

        total = sum(counts_dict.values())

        return {"status": "success", "data": {"total": total, "by_type": counts_dict}}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Failed to get profile counts", "error": str(e)},
        )


@router.get("/profiles/{user_id}", response_model=dict[str, Any])
def get_profile_with_names(user_id: str, db: Session = Depends(get_db)):
    """Get a specific profile with all associated identity names."""
    try:
        profile = (
            db.query(BaseProfile)
            .filter(BaseProfile.user_id == user_id, BaseProfile.deleted_at.is_(None))
            .first()
        )

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        names = db.query(IdentityName).filter(IdentityName.identity_id == profile.user_id).all()

        return {
            "status": "success",
            "data": {
                "profile": {
                    "user_id": str(profile.user_id),
                    "account_type": profile.account_type.value,
                    "legal_name": profile.legal_name,
                    "primary_email": profile.primary_email,
                    "primary_phone": profile.primary_phone,
                    "preferred_language": profile.preferred_language,
                    "created_at": profile.created_at.isoformat() if profile.created_at else None,
                    "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
                },
                "names": [
                    {
                        "id": str(name.id),
                        "type": name.name_type.value,
                        "value": name.name_value,
                        "is_primary": name.is_primary,
                        "is_deprecated": name.is_deprecated,
                        "visibility_level": name.visibility_level.value,
                        "created_at": name.created_at.isoformat() if name.created_at else None,
                    }
                    for name in names
                ],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Failed to get profile", "error": str(e)},
        )
