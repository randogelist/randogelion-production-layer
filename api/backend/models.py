from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CustomerStatus(str, Enum):
    pending = "pending"
    active = "active"
    unsubscribe_pending = "unsubscribe_pending"
    unsubscribed = "unsubscribed"
    suspended = "suspended"


class JobStatus(str, Enum):
    queued = "queued"
    claimed = "claimed"
    complete = "complete"
    failed = "failed"


class MarketplaceCustomer(BaseModel):
    internal_customer_id: str
    customer_identifier: str
    customer_aws_account_id: str | None = None
    product_code: str
    license_arn: str | None = None
    status: CustomerStatus = CustomerStatus.pending
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ApiKeyRecord(BaseModel):
    api_key_id: str
    internal_customer_id: str
    api_key_hash: str
    created_at: datetime = Field(default_factory=utcnow)
    disabled: bool = False


class RandomRequest(BaseModel):
    bytes: int = Field(gt=0, le=1_000_000_000, description="Number of random bytes requested")
    delivery: Literal["auto", "direct", "job"] = "auto"


class RandomDirectResponse(BaseModel):
    mode: Literal["direct"] = "direct"
    bytes: int
    encoding: Literal["base64"] = "base64"
    data_b64: str
    request_id: str


class RandomJobResponse(BaseModel):
    mode: Literal["job"] = "job"
    job_id: str
    status: JobStatus
    bytes: int
    request_id: str


class JobRecord(BaseModel):
    job_id: str
    request_id: str
    internal_customer_id: str
    requested_bytes: int
    status: JobStatus = JobStatus.queued
    claimed_by: str | None = None
    output_s3_key: str | None = None
    output_sha256: str | None = None
    output_bytes: int | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    requested_bytes: int
    output_s3_key: str | None = None
    output_sha256: str | None = None
    download_url: str | None = None
    error: str | None = None


class WorkerClaimResponse(BaseModel):
    job_id: str | None = None
    request_id: str | None = None
    bytes: int | None = None
    upload_mode: Literal["s3"] = "s3"
    s3_bucket: str | None = None
    s3_key: str | None = None
    message: str


class WorkerCompleteRequest(BaseModel):
    s3_key: str
    bytes: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)


class UsageRecord(BaseModel):
    usage_id: str
    internal_customer_id: str
    customer_identifier: str
    dimension: str
    quantity_gb: int
    raw_bytes: int
    metered: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    metered_at: datetime | None = None
