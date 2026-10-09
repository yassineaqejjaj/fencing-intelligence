#!/usr/bin/env python3
"""Mirror an S3-compatible bucket to/from a local directory.

Only dependency is boto3 (``pip install boto3``). Credentials and endpoint
come from the same S3_* environment variables the API uses:

    S3_ENDPOINT_URL S3_ACCESS_KEY S3_SECRET_KEY S3_BUCKET S3_REGION

Usage:
    scripts/s3_mirror.py backup <local-dir>
    scripts/s3_mirror.py restore <local-dir>

Backup downloads every key the mirror does not already have at the same
size, so repeated runs are incremental. Restore uploads local files whose
size differs (or that are missing) and never deletes remote keys, so a
restore cannot wipe newer video bytes.
"""
import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config


def _client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000"),
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )


def backup(root: Path) -> tuple[int, int]:
    client = _client()
    bucket = os.environ["S3_BUCKET"]
    root.mkdir(parents=True, exist_ok=True)
    paginator = client.get_paginator("list_objects_v2")
    count, total = 0, 0
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            key = item["Key"]
            target = root / key
            if target.exists() and target.stat().st_size == item["Size"]:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, str(target))
            count += 1
            total += item["Size"]
    return count, total


def restore(root: Path) -> tuple[int, int]:
    client = _client()
    bucket = os.environ["S3_BUCKET"]
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)
    existing: dict[str, int] = {}
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            existing[item["Key"]] = item["Size"]
    count, total = 0, 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        key = path.relative_to(root).as_posix()
        size = path.stat().st_size
        if existing.get(key) == size:
            continue
        client.upload_file(str(path), bucket, key)
        count += 1
        total += size
    return count, total


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in {"backup", "restore"}:
        print(__doc__.strip().splitlines()[-4], file=sys.stderr)
        raise SystemExit(2)
    for variable in ("S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET"):
        if not os.environ.get(variable):
            print(f"s3_mirror: {variable} is not set", file=sys.stderr)
            raise SystemExit(1)
    mode, target = sys.argv[1], Path(sys.argv[2])
    count, total = backup(target) if mode == "backup" else restore(target)
    print(f"s3_mirror {mode}: {count} file(s), {total} bytes <-> {target}")


if __name__ == "__main__":
    main()
