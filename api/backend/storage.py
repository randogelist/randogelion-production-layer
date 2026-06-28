import base64
from datetime import timedelta

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from api.backend.config import Settings


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.s3 = boto3.client("s3", region_name=settings.aws_region)

    def make_job_output_key(self, job_id: str) -> str:
        return f"rng-output/{job_id}.bin"

    def presign_download(self, s3_key: str, expires_seconds: int = 900) -> str | None:
        if self.settings.local_dev_allow_fake_marketplace:
            return f"dev-s3://{self.settings.s3_bucket}/{s3_key}?expires={expires_seconds}"
        try:
            return self.s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.settings.s3_bucket, "Key": s3_key},
                ExpiresIn=expires_seconds,
            )
        except (BotoCoreError, ClientError):
            return None

    def presign_upload(self, s3_key: str, expires_seconds: int = 900) -> str | None:
        if self.settings.local_dev_allow_fake_marketplace:
            return f"dev-s3-upload://{self.settings.s3_bucket}/{s3_key}?expires={expires_seconds}"
        try:
            return self.s3.generate_presigned_url(
                ClientMethod="put_object",
                Params={"Bucket": self.settings.s3_bucket, "Key": s3_key},
                ExpiresIn=expires_seconds,
            )
        except (BotoCoreError, ClientError):
            return None
