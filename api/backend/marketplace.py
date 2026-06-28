import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from api.backend.config import Settings
from api.backend.db import Repository
from api.backend.models import CustomerStatus, MarketplaceCustomer, UsageRecord


class MarketplaceError(RuntimeError):
    pass


class MarketplaceClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = boto3.client("meteringmarketplace", region_name=settings.aws_region)

    def resolve_customer(self, registration_token: str) -> dict:
        if self.settings.local_dev_allow_fake_marketplace and registration_token.startswith("dev-"):
            fake_id = registration_token.replace("dev-", "customer-", 1)
            return {
                "CustomerIdentifier": fake_id,
                "CustomerAWSAccountId": "000000000000",
                "ProductCode": self.settings.aws_marketplace_product_code,
                "LicenseArn": f"arn:aws:license-manager::000000000000:license:{fake_id}",
            }
        try:
            return self.client.resolve_customer(RegistrationToken=registration_token)
        except (BotoCoreError, ClientError) as exc:
            raise MarketplaceError(str(exc)) from exc

    def batch_meter_usage(self, usage_records: list[UsageRecord]) -> dict:
        if not usage_records:
            return {"Results": []}
        aws_records = [
            {
                "CustomerIdentifier": record.customer_identifier,
                "Dimension": record.dimension,
                "Quantity": record.quantity,
                "Timestamp": record.created_at,
            }
            for record in usage_records
        ]
        if self.settings.local_dev_allow_fake_marketplace:
            return {"Results": [{"MeteringRecordId": record.usage_id, "Status": "Success"} for record in usage_records]}
        try:
            return self.client.batch_meter_usage(
                ProductCode=self.settings.aws_marketplace_product_code,
                UsageRecords=aws_records,
            )
        except (BotoCoreError, ClientError) as exc:
            raise MarketplaceError(str(exc)) from exc


def create_or_get_customer_from_token(token: str, repo: Repository, client: MarketplaceClient) -> MarketplaceCustomer:
    resolved = client.resolve_customer(token)
    existing = repo.get_customer_by_marketplace_id(resolved["CustomerIdentifier"])
    if existing:
        return existing
    customer = MarketplaceCustomer(
        internal_customer_id=str(uuid.uuid4()),
        customer_identifier=resolved["CustomerIdentifier"],
        customer_aws_account_id=resolved.get("CustomerAWSAccountId"),
        product_code=resolved["ProductCode"],
        license_arn=resolved.get("LicenseArn"),
        status=CustomerStatus.pending,
    )
    return repo.upsert_customer(customer)


def apply_sns_subscription_message(message: dict, repo: Repository) -> dict:
    """Apply Marketplace subscription lifecycle messages.

    AWS SNS sends an envelope. The actual Marketplace message is usually inside
    the `Message` field as a JSON string. For local tests we also accept the
    inner object directly.
    """
    inner = message
    if "Message" in message and isinstance(message["Message"], str):
        try:
            inner = json.loads(message["Message"])
        except json.JSONDecodeError:
            inner = {"raw_message": message["Message"]}

    action = inner.get("action") or inner.get("Action")
    customer_identifier = inner.get("customer-identifier") or inner.get("customerIdentifier") or inner.get("CustomerIdentifier")

    status_map = {
        "subscribe-success": CustomerStatus.active,
        "subscribe-fail": CustomerStatus.suspended,
        "unsubscribe-pending": CustomerStatus.unsubscribe_pending,
        "unsubscribe-success": CustomerStatus.unsubscribed,
    }

    if action in status_map and customer_identifier:
        repo.set_customer_status(customer_identifier, status_map[action])
        return {"applied": True, "action": action, "customer_identifier": customer_identifier}
    return {"applied": False, "reason": "unsupported or incomplete message", "action": action}


def meter_unmetered_usage(repo: Repository, client: MarketplaceClient) -> dict:
    records = repo.list_unmetered_usage()
    grouped: dict[str, list[UsageRecord]] = defaultdict(list)
    for record in records:
        # BatchMeterUsage accepts one product per call. This blueprint assumes
        # one Marketplace product; grouping by dimension/customer is kept simple.
        grouped[record.dimension].append(record)

    metered_ids: list[str] = []
    results: list[dict] = []
    for dimension, dim_records in grouped.items():
        response = client.batch_meter_usage(dim_records)
        results.append({"dimension": dimension, "aws_response": response})
        metered_ids.extend(record.usage_id for record in dim_records)
    repo.mark_usage_metered(metered_ids)
    return {"metered_count": len(metered_ids), "results": results}
