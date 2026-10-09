import os
import uuid

import pytest
import redis

from fencing_api.deps import enforce_rate_limit
from fencing_api.errors import AppError


def test_upload_rate_limit_blocks_abuse():
    cache = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    key = f"upload-rate-test:{uuid.uuid4()}"
    for _ in range(3):
        enforce_rate_limit(cache, key, 3, 60)
    with pytest.raises(AppError) as caught:
        enforce_rate_limit(cache, key, 3, 60)
    assert caught.value.status_code == 429
