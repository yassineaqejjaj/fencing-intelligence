import logging
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from fencing_api.config import Settings, get_settings
from fencing_api.errors import AppError


def _client(settings: Settings, *, public: bool):
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint_url if public else settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    client = _client(settings, public=False)
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        try:
            client.create_bucket(Bucket=settings.s3_bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                raise
    try:
        client.put_bucket_cors(
            Bucket=settings.s3_bucket,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedOrigins": settings.cors_origin_list or ["http://localhost:3000"],
                        "AllowedMethods": ["GET", "PUT", "HEAD"],
                        "AllowedHeaders": ["*"],
                        "ExposeHeaders": ["ETag"],
                        "MaxAgeSeconds": 3000,
                    }
                ]
            },
        )
    except ClientError:
        logging.getLogger(__name__).warning("object storage did not accept a CORS configuration")


def upload_file(path: Path, key: str, content_type: str, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    _client(settings, public=False).upload_file(
        str(path),
        settings.s3_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return path.stat().st_size


def upload_bytes(data: bytes, key: str, content_type: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    _client(settings, public=False).put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def download_file(key: str, path: Path, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    path.parent.mkdir(parents=True, exist_ok=True)
    _client(settings, public=False).download_file(settings.s3_bucket, key, str(path))


def delete_key(key: str, settings: Settings | None = None) -> None:
    if not key:
        return
    settings = settings or get_settings()
    _client(settings, public=False).delete_object(Bucket=settings.s3_bucket, Key=key)


def head(key: str, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    try:
        return _client(settings, public=False).head_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as exc:
        raise AppError("not_found", 404, "Uploaded object was not found") from exc


def presign_put(key: str, content_type: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return _client(settings, public=True).generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=3600,
    )


def presign_get(key: str, settings: Settings | None = None, download_name: str | None = None) -> str:
    settings = settings or get_settings()
    params = {"Bucket": settings.s3_bucket, "Key": key}
    if download_name:
        params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'
    return _client(settings, public=True).generate_presigned_url("get_object", Params=params, ExpiresIn=900)


def read_bytes(key: str, settings: Settings | None = None) -> bytes:
    settings = settings or get_settings()
    response = _client(settings, public=False).get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read()
