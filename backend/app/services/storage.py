from __future__ import annotations

from io import BytesIO
from uuid import uuid4

from minio import Minio
from minio.error import S3Error


class StorageService:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool,
        buckets: list[str],
    ) -> None:
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.buckets = buckets

    async def ensure_buckets(self) -> None:
        for bucket in self.buckets:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            list(self.client.list_buckets())
            return True, "ok"
        except Exception as exc:  # pragma: no cover - exercised in integration
            return False, str(exc)

    async def smoke_test(self) -> tuple[bool, str]:
        if not self.buckets:
            return False, "no buckets configured"
        bucket = self.buckets[0]
        object_name = f"health/{uuid4()}.txt"
        try:
            payload = b"science-pub-healthcheck"
            self.client.put_object(bucket, object_name, BytesIO(payload), len(payload))
            response = self.client.get_object(bucket, object_name)
            body = response.read()
            self.client.remove_object(bucket, object_name)
            if body != payload:
                return False, "payload mismatch"
            return True, "ok"
        except S3Error as exc:  # pragma: no cover - exercised in integration
            return False, str(exc)

