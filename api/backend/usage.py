import math
import uuid

from api.backend.config import Settings
from api.backend.db import Repository
from api.backend.models import MarketplaceCustomer, UsageRecord


def gb_ceil(byte_count: int) -> int:
    # Marketplace dimensions are commonly integer quantities. This blueprint
    # rounds up delivered bytes to whole GB. Change to MiB/GiB or decimal GB
    # only before product submission, because dimension semantics should remain stable.
    return max(1, math.ceil(byte_count / 1_000_000_000))


def record_delivered_usage(
    repo: Repository,
    settings: Settings,
    customer: MarketplaceCustomer,
    delivered_bytes: int,
) -> UsageRecord:
    usage = UsageRecord(
        usage_id=str(uuid.uuid4()),
        internal_customer_id=customer.internal_customer_id,
        customer_identifier=customer.customer_identifier,
        dimension=settings.aws_marketplace_dimension,
        quantity_gb=gb_ceil(delivered_bytes),
        raw_bytes=delivered_bytes,
    )
    return repo.add_usage(usage)
