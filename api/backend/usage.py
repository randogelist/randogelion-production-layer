import math
import uuid

from api.backend.config import Settings
from api.backend.db import Repository
from api.backend.models import MarketplaceCustomer, Plan, UsageRecord


def units_2048bit(byte_count: int, unit_bytes: int) -> int:
    return max(1, math.ceil(byte_count / unit_bytes))


def record_delivered_usage(
    repo: Repository,
    settings: Settings,
    customer: MarketplaceCustomer,
    delivered_bytes: int,
    request_id: str,
    plan_charged: Plan,
) -> UsageRecord:
    usage = UsageRecord(
        usage_id=str(uuid.uuid4()),
        request_id=request_id,
        internal_customer_id=customer.internal_customer_id,
        customer_identifier=customer.customer_identifier,
        dimension=settings.aws_marketplace_dimension,
        quantity=units_2048bit(delivered_bytes, settings.rng_unit_bytes),
        raw_bytes=delivered_bytes,
        plan_charged=plan_charged,
        billable=(plan_charged != Plan.free),
    )
    return repo.add_usage(usage)
