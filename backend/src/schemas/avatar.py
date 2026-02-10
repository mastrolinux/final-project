"""
Avatar Schemas

Pydantic models for avatar upload and delete response validation.
Upload requests use FastAPI's UploadFile (multipart/form-data), so no
request schema is needed here.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AvatarResponse(BaseModel):
    """Response schema returned after a successful avatar upload."""

    avatar_url: str = Field(
        ..., description="Public URL of the avatar image (400x400 WebP)"
    )
    avatar_thumbnail_url: str = Field(
        ..., description="Public URL of the avatar thumbnail (80x80 WebP)"
    )
    message: str = Field(
        default="Avatar uploaded successfully",
        description="Human-readable status message",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "avatar_url": "https://storage.example.com/avatars/user-id/avatar.webp",
                    "avatar_thumbnail_url": "https://storage.example.com/avatars/user-id/thumbnail.webp",
                    "message": "Avatar uploaded successfully",
                }
            ]
        }
    )


class AvatarDeleteResponse(BaseModel):
    """Response schema returned after a successful avatar deletion."""

    message: str = Field(
        default="Avatar deleted successfully",
        description="Human-readable status message",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Avatar deleted successfully",
                }
            ]
        }
    )
