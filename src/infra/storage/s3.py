"""S3/MinIO storage for ingest files and other blobs."""
from uuid import UUID

from src.config import get_settings


def get_s3_client():
    """Return boto3 S3 client configured from settings."""
    import boto3
    from botocore.config import Config

    s = get_settings().s3
    return boto3.client(
        "s3",
        endpoint_url=s.endpoint_url,
        aws_access_key_id=s.access_key,
        aws_secret_access_key=s.secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def put_ingest_file(batch_id: UUID, content: bytes, filename: str) -> str:
    """Store ingest file in S3; return key."""
    client = get_s3_client()
    bucket = get_settings().s3.bucket
    key = f"ingest/{batch_id}/{filename}"
    client.put_object(Bucket=bucket, Key=key, Body=content)
    return key


def get_ingest_file(key: str) -> bytes:
    """Retrieve file content from S3 by key."""
    client = get_s3_client()
    bucket = get_settings().s3.bucket
    resp = client.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def get_latest_ingest_file(batch_id: UUID) -> tuple[str, bytes]:
    """Find and return latest ingest object for batch."""
    client = get_s3_client()
    bucket = get_settings().s3.bucket
    prefix = f"ingest/{batch_id}/"
    resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contents = resp.get("Contents", [])
    if not contents:
        raise FileNotFoundError(f"No ingest file found for batch {batch_id}")
    latest = max(contents, key=lambda item: item.get("LastModified"))
    key = latest["Key"]
    return key, get_ingest_file(key)
