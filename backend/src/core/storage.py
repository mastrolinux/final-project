"""
Protocol-based storage abstraction with Supabase and in-memory implementations.
"""

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class StorageUploadResult:
    """Outcome of a successful upload operation."""

    storage_path: str
    public_url: str


@runtime_checkable
class StorageClient(Protocol):
    """Structural interface for blob storage operations (PEP 544)."""

    def upload(self, path: str, data: bytes, content_type: str) -> StorageUploadResult:
        """Upload a blob and return its storage path and public URL."""
        ...

    def delete(self, path: str) -> bool:
        """Delete a blob by storage path. Returns True if the object existed."""
        ...

    def get_public_url(self, path: str) -> str:
        """Return the public URL for a given storage path."""
        ...

    def download(self, path: str) -> bytes | None:
        """Download a blob by storage path. Returns None if not found."""
        ...


class SupabaseStorageClient:
    """Supabase Storage client for the public ``avatars`` bucket."""

    BUCKET = "avatars"

    def __init__(self, supabase_url: str, supabase_key: str, public_url: str = ""):
        from supabase import create_client

        self._client = create_client(supabase_url, supabase_key)
        self._supabase_url = supabase_url.rstrip("/")
        self._public_url = public_url.rstrip("/") if public_url else ""
        self._bucket_confirmed = False
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the avatars bucket if it does not already exist."""
        try:
            self._client.storage.get_bucket(self.BUCKET)
            self._bucket_confirmed = True
            logger.info("Storage bucket '%s' exists", self.BUCKET)
        except Exception:
            try:
                self._client.storage.create_bucket(
                    self.BUCKET,
                    options={"public": True},
                )
                self._bucket_confirmed = True
                logger.info("Created storage bucket '%s'", self.BUCKET)
            except Exception as exc:
                logger.warning(
                    "Could not create bucket '%s': %s. Will retry on first upload.",
                    self.BUCKET,
                    exc,
                )

    def upload(self, path: str, data: bytes, content_type: str) -> StorageUploadResult:
        """Upload to Supabase Storage, overwriting any existing object at the path."""
        if not self._bucket_confirmed:
            self._ensure_bucket()
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
        """Return the public URL, rewriting Docker-internal URLs if needed."""
        url = self._client.storage.from_(self.BUCKET).get_public_url(path)
        if self._public_url and self._supabase_url in url:
            url = url.replace(self._supabase_url, self._public_url, 1)
        return url

    def download(self, path: str) -> bytes | None:
        """Download raw bytes from Supabase Storage."""
        try:
            data = self._client.storage.from_(self.BUCKET).download(path)
            logger.info("Downloaded %s/%s", self.BUCKET, path)
            return data
        except Exception:
            logger.warning("Failed to download %s/%s", self.BUCKET, path, exc_info=True)
            return None


class SupabaseDocumentStorageClient:
    """Supabase Storage client for the private ``verification-documents`` bucket."""

    BUCKET = "verification-documents"

    def __init__(self, supabase_url: str, supabase_key: str, public_url: str = ""):
        from supabase import create_client

        self._client = create_client(supabase_url, supabase_key)
        self._supabase_url = supabase_url.rstrip("/")
        self._public_url = public_url.rstrip("/") if public_url else ""
        self._bucket_confirmed = False
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the private bucket if it does not already exist."""
        try:
            self._client.storage.get_bucket(self.BUCKET)
            self._bucket_confirmed = True
            logger.info("Storage bucket '%s' exists", self.BUCKET)
        except Exception:
            try:
                self._client.storage.create_bucket(
                    self.BUCKET,
                    options={"public": False},
                )
                self._bucket_confirmed = True
                logger.info("Created private storage bucket '%s'", self.BUCKET)
            except Exception as exc:
                logger.warning(
                    "Could not create bucket '%s': %s. Will retry on first upload.",
                    self.BUCKET,
                    exc,
                )

    def upload(self, path: str, data: bytes, content_type: str) -> StorageUploadResult:
        """Upload encrypted bytes to the private bucket."""
        if not self._bucket_confirmed:
            self._ensure_bucket()
        self._client.storage.from_(self.BUCKET).upload(
            path,
            data,
            file_options={
                "content-type": "application/octet-stream",
                "upsert": "true",
            },
        )
        logger.info("Uploaded %d bytes to %s/%s", len(data), self.BUCKET, path)
        return StorageUploadResult(storage_path=path, public_url="")

    def delete(self, path: str) -> bool:
        """Remove an object from the private bucket."""
        try:
            self._client.storage.from_(self.BUCKET).remove([path])
            logger.info("Deleted %s/%s", self.BUCKET, path)
            return True
        except Exception:
            logger.warning("Failed to delete %s/%s", self.BUCKET, path, exc_info=True)
            return False

    def get_public_url(self, path: str) -> str:
        """Documents in the private bucket do not have public URLs."""
        return ""

    def download(self, path: str) -> bytes | None:
        """Download encrypted bytes from the private bucket."""
        try:
            data = self._client.storage.from_(self.BUCKET).download(path)
            logger.info("Downloaded %s/%s", self.BUCKET, path)
            return data
        except Exception:
            logger.warning("Failed to download %s/%s", self.BUCKET, path, exc_info=True)
            return None


class InMemoryStorageClient:
    """Test double for StorageClient backed by a plain dict."""

    BASE_URL = "https://storage.test"

    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}

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

    def download(self, path: str) -> bytes | None:
        return self.blobs.get(path)


_storage_client: StorageClient | None = None
_document_storage_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    """FastAPI dependency returning the configured StorageClient singleton."""
    if _storage_client is None:
        raise RuntimeError(
            "Storage client not configured. Call configure_storage_client() at application startup."
        )
    return _storage_client


def configure_storage_client(client: StorageClient) -> None:
    """Set the global storage client singleton (called once at startup)."""
    global _storage_client
    _storage_client = client


def get_document_storage_client() -> StorageClient:
    """FastAPI dependency returning the document storage client singleton."""
    if _document_storage_client is None:
        raise RuntimeError(
            "Document storage client not configured. "
            "Call configure_document_storage_client() at application startup."
        )
    return _document_storage_client


def configure_document_storage_client(client: StorageClient) -> None:
    """Set the global document storage client singleton."""
    global _document_storage_client
    _document_storage_client = client
