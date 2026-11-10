"""Adaptateur de stockage objet compatible S3 (SeaweedFS en local, S3 ou équivalent en production)."""
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.core.config import get_settings


@lru_cache
def s3_client() -> BaseClient:
    s = get_settings()
    if not (s.s3_access_key and s.s3_secret_key):
        raise RuntimeError("S3_ACCESS_KEY / S3_SECRET_KEY non configurés.")
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
    )


def ensure_bucket(name: str) -> None:
    client = s3_client()
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if name not in existing:
        client.create_bucket(Bucket=name)
