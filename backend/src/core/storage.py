"""
Storage Abstraction Module

Provides a Protocol-based storage interface with two implementations:

    SupabaseStorageClient  -- production client backed by Supabase Storage
    InMemoryStorageClient  -- test double that stores blobs in a dict

The Protocol uses structural subtyping (PEP 544), so any object exposing
the three required methods is accepted without explicit registration.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class StorageUploadResult:
    """Outcome of a successful upload operation."""
    storage_path: str
    public_url: str


@runtime_checkable
class StorageClient(Protocol):
    """
    Structural interface for blob storage operations.

    Implementations must provide upload, delete, and public URL retrieval.
    """

    def upload(self, path: str, data: bytes, content_type: str) -> StorageUploadResult:
        """Upload a blob and return its storage path and public URL."""
        ...

    def delete(self, path: str) -> bool:
        """Delete a blob by storage path. Returns True if the object existed."""
        ...

    def get_public_url(self, path: str) -> str:
        """Return the public URL for a given storage path."""
        ...


class SupabaseStorageClient:
    """
    Production storage client using Supabase Storage (S3-compatible).

    Requires the ``supabase`` Python SDK and a configured bucket named ``avatars``.
    The bucket must have public access enabled so avatar URLs are directly
    resolvable without signed tokens.
    """

    BUCKET = "avatars"

    def __init__(self, supabase_url: str, supabase_key: str, public_url: str = ""):
        from supabase import create_client
        self._client = create_client(supabase_url, supabase_key)
        self._supabase_url = supabase_url.rstrip("/")
        self._public_url = public_url.rstrip("/") if public_url else ""
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the avatars bucket if it does not already exist."""
        try:
            self._client.storage.get_bucket(self.BUCKET)
            logger.info("Storage bucket '%s' exists", self.BUCKET)
        except Exception:
            try:
                self._client.storage.create_bucket(
                    self.BUCKET,
                    options={"public": True},
                )
                logger.info("Created storage bucket '%s'", self.BUCKET)
            except Exception as exc:
                logger.warning(
                    "Could not create bucket '%s': %s. "
                    "Uploads will fail until the bucket is created manually.",
                    self.BUCKET, exc,
                )

    def upload(self, path: str, data: bytes, content_type: str) -> StorageUploadResult:
        """Upload to Supabase Storage, overwriting any existing object at the path."""
        self._client.storage.from_(self.BUCKET).upload(
            path,
            data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        public_url = self.get_public_url(path)
        logger.info("Uploaded %d bytes to %s/%s", len(data), self.BUCKET, path)
        return StorageUploadResult(storage_path=path, public_url=public_url)

    def delete(self, path: str) -> bool:
        """Remove an object from Supabase Storage."""
        try:
            self._client.storage.from_(self.BUCKET).remove([path])
            logger.info("Deleted %s/%s", self.BUCKET, path)
            return True
        except Exception:
            logger.warning("Failed to delete %s/%s", self.BUCKET, path, exc_info=True)
            return False

    def get_public_url(self, path: str) -> str:
        """Return the public URL for an object in the avatars bucket.

        When a separate ``public_url`` was provided (e.g. the host-facing
        Supabase URL that differs from the Docker-internal one), the SDK
        URL is rewritten so that browsers can resolve it.
        """
        url = self._client.storage.from_(self.BUCKET).get_public_url(path)
        if self._public_url and self._supabase_url in url:
            url = url.replace(self._supabase_url, self._public_url, 1)
        return url


class InMemoryStorageClient:
    """
    Test double for StorageClient.

    Stores blobs in a plain dict keyed by storage path. Useful for unit and
    integration tests that must not depend on external services.
    """

    BASE_URL = "https://storage.test"

    def __init__(self) -> None:
        self.blobs: Dict[str, bytes] = {}

    def upload(self, path: str, data: bytes, content_type: str) -> StorageUploadResult:
        self.blobs[path] = data
        public_url = self.get_public_url(path)
        return StorageUploadResult(storage_path=path, public_url=public_url)

    def delete(self, path: str) -> bool:
        existed = path in self.blobs
        self.blobs.pop(path, None)
        return existed

    def get_public_url(self, path: str) -> str:
        return f"{self.BASE_URL}/{path}"


# ---------------------------------------------------------------------------
# Dependency injection helper
# ---------------------------------------------------------------------------

_storage_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """
    FastAPI dependency that returns the configured StorageClient singleton.

    In production, call ``configure_storage_client`` at application startup.
    In tests, override this dependency with ``InMemoryStorageClient``.
    """
    if _storage_client is None:
        raise RuntimeError(
            "Storage client not configured. "
            "Call configure_storage_client() at application startup."
        )
    return _storage_client


def configure_storage_client(client: StorageClient) -> None:
    """Set the global storage client singleton (called once at startup)."""
    global _storage_client
    _storage_client = client
