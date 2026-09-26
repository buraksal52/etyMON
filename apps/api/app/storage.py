from typing import Protocol

import boto3

from app.settings import settings


class StorageProvider(Protocol):
    def put_bytes(self, key: str, content: bytes, content_type: str) -> None: ...

    def get_download_url(self, key: str, expires_in: int = 900) -> str: ...


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


def get_storage_provider() -> StorageProvider:
    return S3StorageProvider()
