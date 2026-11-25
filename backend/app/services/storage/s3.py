import asyncio
from typing import Any
import boto3
from botocore.exceptions import ClientError
from app.services.storage.base import StorageDriver
from app.config import settings


class S3StorageDriver(StorageDriver):
    """Pilote de stockage pour S3 et compatibles (MinIO, Cloudflare R2, Scaleway, AWS)."""

    def __init__(
        self,
        bucket_name: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str | None = None,
    ):
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME or "hierici-media"
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key_id = access_key_id or settings.S3_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.S3_SECRET_ACCESS_KEY
        self.region = region or settings.S3_REGION or "fr-par"

        self._client: Any = None

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
            )
        return self._client

    def _clean_path(self, path: str) -> str:
        return path.lstrip("/")

    async def save(
        self,
        content: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        key = self._clean_path(destination_path)
        client = self._get_client()

        def _upload():
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type,
            )

        await asyncio.to_thread(_upload)
        return await self.get_url(key)

    async def read(self, path: str) -> bytes:
        key = self._clean_path(path)
        client = self._get_client()

        def _download():
            try:
                response = client.get_object(Bucket=self.bucket_name, Key=key)
                return response["Body"].read()
            except ClientError as e:
                if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                    raise FileNotFoundError(f"Objet introuvable dans le bucket S3 : {path}")
                raise

        return await asyncio.to_thread(_download)

    async def delete(self, path: str) -> bool:
        if not await self.exists(path):
            return False
        key = self._clean_path(path)
        client = self._get_client()

        def _delete():
            try:
                client.delete_object(Bucket=self.bucket_name, Key=key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_delete)

    async def exists(self, path: str) -> bool:
        key = self._clean_path(path)
        client = self._get_client()

        def _head():
            try:
                client.head_object(Bucket=self.bucket_name, Key=key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)

    def resolve_url(self, path: str) -> str:
        key = self._clean_path(path)
        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{key}"
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"

    async def get_url(self, path: str) -> str:
        return self.resolve_url(path)

