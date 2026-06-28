from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_name: str = "aws-rng-api-blueprint"
    aws_region: str = "us-east-1"

    aws_marketplace_product_code: str = "replace-me"

    # Marketplace billing dimension. For the first product version we meter
    # request-sized 2048-bit units. Larger requests are converted into units.
    aws_marketplace_dimension: str = "RNG2048BitUnits"

    api_key_pepper: str = "dev-pepper-change-me"
    worker_shared_token: str = "dev-worker-token-change-me"
    local_dev_allow_fake_marketplace: bool = True

    # Product limits.
    rng_unit_bytes: int = 256                      # 2048 bit request unit
    free_tier_bytes: int = 2 * 1024 * 1024         # 2 MiB free total per customer
    free_tier_max_request_bytes: int = 256         # free tier only serves 2048-bit units
    paid_max_request_bytes: int = 2 * 1024 * 1024  # paid tier up to 2 MiB per request
    max_direct_response_bytes: int = 2 * 1024 * 1024

    # Embedded monthly inventory.
    rng_provider: str = "embedded_magazine"
    rng_magazine_path: str = "/app/data/rng_magazine.bin"
    rng_magazine_max_request_bytes: int = 2 * 1024 * 1024

    # Local worker/S3 placeholders for later large-delivery jobs.
    s3_bucket: str = "replace-me"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
