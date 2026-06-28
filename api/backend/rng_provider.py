import base64
import os
import threading
import uuid

from api.backend.config import Settings
from api.backend.db import Repository
from api.backend.models import (
    JobRecord,
    JobStatusResponse,
    MarketplaceCustomer,
    RandomDirectResponse,
    RandomJobResponse,
    RandomRequest,
)
from api.backend.storage import ObjectStorage
from api.backend.usage import record_delivered_usage

_MAGAZINE_LOCK = threading.Lock()
_MAGAZINE_OFFSETS: dict[str, int] = {}


def get_embedded_magazine_status(settings: Settings) -> dict:
    path = settings.rng_magazine_path
    exists = os.path.isfile(path)
    size = os.path.getsize(path) if exists else 0
    consumed = _MAGAZINE_OFFSETS.get(path, 0)
    remaining = max(size - consumed, 0)
    return {
        "provider": settings.rng_provider,
        "path": path,
        "exists": exists,
        "size_bytes": size,
        "consumed_bytes": consumed,
        "remaining_bytes": remaining,
        "max_request_bytes": settings.rng_magazine_max_request_bytes,
        "remaining_1024_byte_requests": remaining // 1024,
        "note": "Pseudo-production test: magazine cursor is in-memory and resets if the ECS task restarts.",
    }


def read_embedded_magazine(settings: Settings, byte_count: int) -> bytes:
    if byte_count > settings.rng_magazine_max_request_bytes:
        raise ValueError(
            f"Embedded magazine direct requests are limited to {settings.rng_magazine_max_request_bytes} bytes"
        )

    path = settings.rng_magazine_path
    if not os.path.isfile(path):
        raise ValueError(f"Embedded RNG magazine not found at {path}")

    with _MAGAZINE_LOCK:
        size = os.path.getsize(path)
        offset = _MAGAZINE_OFFSETS.get(path, 0)

        if offset + byte_count > size:
            remaining = max(size - offset, 0)
            raise ValueError(f"Embedded RNG magazine exhausted: requested={byte_count}, remaining={remaining}")

        with open(path, "rb") as handle:
            handle.seek(offset)
            data = handle.read(byte_count)

        if len(data) != byte_count:
            raise ValueError(f"Embedded RNG magazine short read: requested={byte_count}, got={len(data)}")

        _MAGAZINE_OFFSETS[path] = offset + byte_count
        return data


class RngService:
    def __init__(self, repo: Repository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings
        self.storage = ObjectStorage(settings)

    def handle_random_request(self, request: RandomRequest, customer: MarketplaceCustomer):
        request_id = str(uuid.uuid4())
        wants_direct = request.delivery == "direct" or (
            request.delivery == "auto" and request.bytes <= self.settings.max_direct_response_bytes
        )

        if wants_direct:
            if request.bytes > self.settings.max_direct_response_bytes:
                raise ValueError("Direct responses above MAX_DIRECT_RESPONSE_BYTES are disabled")

            if self.settings.rng_provider == "embedded_magazine":
                data = read_embedded_magazine(self.settings, request.bytes)
            elif self.settings.rng_provider == "os_urandom":
                data = os.urandom(request.bytes)
            else:
                raise ValueError(f"Unknown RNG_PROVIDER={self.settings.rng_provider}")

            record_delivered_usage(self.repo, self.settings, customer, request.bytes)
            return RandomDirectResponse(
                bytes=request.bytes,
                data_b64=base64.b64encode(data).decode("ascii"),
                request_id=request_id,
            )

        job = JobRecord(
            job_id=str(uuid.uuid4()),
            request_id=request_id,
            internal_customer_id=customer.internal_customer_id,
            requested_bytes=request.bytes,
        )
        self.repo.create_job(job)
        return RandomJobResponse(
            job_id=job.job_id,
            status=job.status,
            bytes=request.bytes,
            request_id=request_id,
        )

    def get_job_status(self, job_id: str, customer: MarketplaceCustomer) -> JobStatusResponse | None:
        job = self.repo.get_job(job_id)
        if not job or job.internal_customer_id != customer.internal_customer_id:
            return None

        download_url = None
        if job.output_s3_key:
            download_url = self.storage.presign_download(job.output_s3_key)

        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            requested_bytes=job.requested_bytes,
            output_s3_key=job.output_s3_key,
            output_sha256=job.output_sha256,
            download_url=download_url,
            error=job.error,
        )

    def complete_worker_job(self, job_id: str, s3_key: str, byte_count: int, sha256: str) -> JobRecord | None:
        job = self.repo.complete_job(job_id, s3_key, byte_count, sha256)
        if not job:
            return None

        customer = self.repo.get_customer_by_internal_id(job.internal_customer_id)
        if customer:
            record_delivered_usage(self.repo, self.settings, customer, byte_count)

        return job
