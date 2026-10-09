from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "dev-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    secret_key: str = DEFAULT_SECRET
    database_url: str = "postgresql+psycopg://fencing:fencing@localhost:5432/fencing"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "fencing"
    s3_secret_key: str = "fencingsecret"
    s3_bucket: str = "fencing-videos"
    s3_region: str = "us-east-1"
    s3_addressing_style: str = "path"
    cookie_secure: bool = False
    session_days: int = 14
    max_upload_bytes: int = 2_000_000_000
    cors_origins: str = "http://localhost:3000"
    inline_jobs: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@localhost"
    smtp_starttls: bool = True
    data_import_root: str = "data/datasets"
    dataset_manifest_root: str = "data/datasets"
    trust_proxy: bool = False
    otel_endpoint: str = ""
    log_level: str = "INFO"
    web_base_url: str = "http://localhost:3000"
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 60
    upload_rate_limit: int = 20
    upload_rate_window_seconds: int = 3600
    ml_service_url: str = ""

    @field_validator("database_url")
    @classmethod
    def _normalize_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def validate_runtime(self) -> None:
        if self.environment == "production":
            problems = []
            if self.secret_key == DEFAULT_SECRET or len(self.secret_key) < 32:
                problems.append("SECRET_KEY must be a unique value of at least 32 characters")
            if self.s3_access_key == "fencing" or self.s3_secret_key == "fencingsecret":
                problems.append("S3 credentials must not use the development defaults")
            if not self.cookie_secure:
                problems.append("COOKIE_SECURE must be true in production")
            if self.inline_jobs:
                problems.append("INLINE_JOBS must be false in production")
            if problems:
                raise RuntimeError("Refusing to start: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
