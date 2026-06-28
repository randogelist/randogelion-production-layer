import hashlib
import secrets
from datetime import datetime, timezone
from threading import RLock
from typing import Iterable

from api.backend.models import (
    ApiKeyRecord,
    CustomerStatus,
    JobRecord,
    JobStatus,
    MarketplaceCustomer,
    UsageRecord,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Repository:
    """Repository boundary.

    The in-memory implementation is for local development only. In production,
    implement the same methods with DynamoDB or Postgres so ECS task restarts do
    not lose customer/job/usage state.
    """

    def upsert_customer(self, customer: MarketplaceCustomer) -> MarketplaceCustomer: ...
    def get_customer_by_internal_id(self, internal_customer_id: str) -> MarketplaceCustomer | None: ...
    def get_customer_by_marketplace_id(self, customer_identifier: str) -> MarketplaceCustomer | None: ...
    def set_customer_status(self, customer_identifier: str, status: CustomerStatus) -> None: ...

    def create_api_key(self, internal_customer_id: str, api_key_hash: str) -> ApiKeyRecord: ...
    def find_api_key_hash(self, api_key_hash: str) -> ApiKeyRecord | None: ...

    def create_job(self, job: JobRecord) -> JobRecord: ...
    def claim_next_job(self, worker_id: str, s3_key: str) -> JobRecord | None: ...
    def get_job(self, job_id: str) -> JobRecord | None: ...
    def complete_job(self, job_id: str, s3_key: str, size: int, sha256: str) -> JobRecord | None: ...
    def fail_job(self, job_id: str, error: str) -> JobRecord | None: ...

    def add_usage(self, usage: UsageRecord) -> UsageRecord: ...
    def list_unmetered_usage(self) -> list[UsageRecord]: ...
    def mark_usage_metered(self, usage_ids: Iterable[str]) -> None: ...


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._lock = RLock()
        self.customers: dict[str, MarketplaceCustomer] = {}
        self.customer_by_marketplace_id: dict[str, str] = {}
        self.api_keys: dict[str, ApiKeyRecord] = {}
        self.jobs: dict[str, JobRecord] = {}
        self.usage: dict[str, UsageRecord] = {}

    def upsert_customer(self, customer: MarketplaceCustomer) -> MarketplaceCustomer:
        with self._lock:
            customer.updated_at = now_utc()
            self.customers[customer.internal_customer_id] = customer
            self.customer_by_marketplace_id[customer.customer_identifier] = customer.internal_customer_id
            return customer

    def get_customer_by_internal_id(self, internal_customer_id: str) -> MarketplaceCustomer | None:
        with self._lock:
            return self.customers.get(internal_customer_id)

    def get_customer_by_marketplace_id(self, customer_identifier: str) -> MarketplaceCustomer | None:
        with self._lock:
            internal_id = self.customer_by_marketplace_id.get(customer_identifier)
            return self.customers.get(internal_id) if internal_id else None

    def set_customer_status(self, customer_identifier: str, status: CustomerStatus) -> None:
        with self._lock:
            customer = self.get_customer_by_marketplace_id(customer_identifier)
            if customer:
                customer.status = status
                customer.updated_at = now_utc()
                self.customers[customer.internal_customer_id] = customer

    def create_api_key(self, internal_customer_id: str, api_key_hash: str) -> ApiKeyRecord:
        with self._lock:
            record = ApiKeyRecord(
                api_key_id=secrets.token_urlsafe(12),
                internal_customer_id=internal_customer_id,
                api_key_hash=api_key_hash,
            )
            self.api_keys[api_key_hash] = record
            return record

    def find_api_key_hash(self, api_key_hash: str) -> ApiKeyRecord | None:
        with self._lock:
            return self.api_keys.get(api_key_hash)

    def create_job(self, job: JobRecord) -> JobRecord:
        with self._lock:
            self.jobs[job.job_id] = job
            return job

    def claim_next_job(self, worker_id: str, s3_key: str) -> JobRecord | None:
        with self._lock:
            queued = sorted(
                (job for job in self.jobs.values() if job.status == JobStatus.queued),
                key=lambda job: job.created_at,
            )
            if not queued:
                return None
            job = queued[0]
            job.status = JobStatus.claimed
            job.claimed_by = worker_id
            job.output_s3_key = s3_key
            job.updated_at = now_utc()
            self.jobs[job.job_id] = job
            return job

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self.jobs.get(job_id)

    def complete_job(self, job_id: str, s3_key: str, size: int, sha256: str) -> JobRecord | None:
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            job.status = JobStatus.complete
            job.output_s3_key = s3_key
            job.output_bytes = size
            job.output_sha256 = sha256
            job.updated_at = now_utc()
            self.jobs[job_id] = job
            return job

    def fail_job(self, job_id: str, error: str) -> JobRecord | None:
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            job.status = JobStatus.failed
            job.error = error
            job.updated_at = now_utc()
            self.jobs[job_id] = job
            return job

    def add_usage(self, usage: UsageRecord) -> UsageRecord:
        with self._lock:
            self.usage[usage.usage_id] = usage
            return usage

    def list_unmetered_usage(self) -> list[UsageRecord]:
        with self._lock:
            return [record for record in self.usage.values() if not record.metered]

    def mark_usage_metered(self, usage_ids: Iterable[str]) -> None:
        with self._lock:
            for usage_id in usage_ids:
                if usage_id in self.usage:
                    self.usage[usage_id].metered = True
                    self.usage[usage_id].metered_at = now_utc()


_repo = InMemoryRepository()


def get_repo() -> Repository:
    return _repo


def hash_api_key(api_key: str, pepper: str) -> str:
    return hashlib.sha256(f"{pepper}:{api_key}".encode("utf-8")).hexdigest()
