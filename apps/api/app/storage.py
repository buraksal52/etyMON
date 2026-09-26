from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import boto3

from app.settings import settings


class StorageProvider(Protocol):
    def put_bytes(self, key: str, content: bytes, content_type: str) -> None: ...

    def get_download_url(self, key: str, expires_in: int = 900) -> str: ...

    def get_bytes(self, key: str) -> tuple[bytes, str]: ...


class S3StorageProvider:
    def __init__(self) -> None:
        self.bucket = settings.storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint or None,
            aws_access_key_id=settings.storage_access_key or None,
            aws_secret_access_key=settings.storage_secret_key or None,
        )

    def put_bytes(self, key: str, content: bytes, content_type: str) -> None:
        if not self.bucket:
            raise RuntimeError("STORAGE_BUCKET is not configured")
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    def get_download_url(self, key: str, expires_in: int = 900) -> str:
        if not self.bucket:
            raise RuntimeError("STORAGE_BUCKET is not configured")
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def get_bytes(self, key: str) -> tuple[bytes, str]:
        if not self.bucket:
            raise RuntimeError("STORAGE_BUCKET is not configured")
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read(), response.get("ContentType", "application/octet-stream")


class LocalFilesystemStorageProvider:
    def __init__(self) -> None:
        self.root = Path(settings.storage_local_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid storage key")
        return path

    def put_bytes(self, key: str, content: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.with_suffix(path.suffix + ".content-type").write_text(content_type)

    def get_download_url(self, key: str, expires_in: int = 900) -> str:
        base_url = settings.storage_public_base_url or "http://localhost:8000"
        return f"{base_url.rstrip('/')}/storage/download?key={quote(key, safe='')}"

    def get_bytes(self, key: str) -> tuple[bytes, str]:
        path = self._path(key)
        content_type_path = path.with_suffix(path.suffix + ".content-type")
        return (
            path.read_bytes(),
            content_type_path.read_text()
            if content_type_path.exists()
            else "application/octet-stream",
        )


def get_storage_provider() -> StorageProvider:
    if settings.storage_provider == "local":
        return LocalFilesystemStorageProvider()
    return S3StorageProvider()
