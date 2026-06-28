from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_name: str = "aws-rng-api-blueprint"
    aws_region: str = "us-east-1"

    aws_marketplace_product_code: str = "replace-me"
    aws_marketplace_dimension: str = "RNGDataGB"

    api_key_pepper: str = "dev-pepper-change-me"
    worker_shared_token: str = "dev-worker-token-change-me"
    local_dev_allow_fake_marketplace: bool = True

    max_direct_response_bytes: int = 1024
    s3_bucket: str = "replace-me"

    # Pseudo-production embedded magazine mode.
    # The Dockerfile copies ./data/rng_magazine.bin into this path.
    rng_provider: str = "embedded_magazine"
    rng_magazine_path: str = "/app/data/rng_magazine.bin"
    rng_magazine_max_request_bytes: int = 1024

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
