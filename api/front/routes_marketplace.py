from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.backend.auth import create_customer_api_key
from api.backend.config import Settings, get_settings
from api.backend.db import Repository, get_repo
from api.backend.marketplace import (
    MarketplaceClient,
    MarketplaceError,
    apply_sns_subscription_message,
    create_or_get_customer_from_token,
    meter_unmetered_usage,
)

router = APIRouter(prefix="/aws/marketplace", tags=["aws-marketplace"])


class RegisterJsonBody(BaseModel):
    x_amzn_marketplace_token: str | None = None
    token: str | None = None


@router.post("/register")
async def register_marketplace_customer(
    request: Request,
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
) -> dict:
    """AWS Marketplace registration endpoint.

    Accepts the real Marketplace form POST field `x-amzn-marketplace-token`.
    For local development it also accepts JSON `{ "token": "dev-demo" }`.
    """
    token = None
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        token = body.get("x-amzn-marketplace-token") or body.get("x_amzn_marketplace_token") or body.get("token")
    else:
        form = await request.form()
        token = form.get("x-amzn-marketplace-token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing x-amzn-marketplace-token")

    client = MarketplaceClient(settings)
    try:
        customer = create_or_get_customer_from_token(token, repo, client)
    except MarketplaceError as exc:
        raise HTTPException(status_code=502, detail=f"Marketplace resolve failed: {exc}") from exc

    api_key = create_customer_api_key(customer, repo, settings)
    return {
        "message": "customer_registered_pending_subscription_event",
        "internal_customer_id": customer.internal_customer_id,
        "marketplace_customer_identifier": customer.customer_identifier,
        "subscription_status": customer.status,
        "api_key": api_key,
        "next_step": "Wait for subscribe-success SNS event before enforcing production access.",
    }


@router.post("/sns")
async def marketplace_sns_webhook(
    request: Request,
    repo: Repository = Depends(get_repo),
) -> dict:
    """Receive AWS Marketplace SNS subscription lifecycle notifications.

    Production TODO: verify SNS signature and handle SubscribeURL confirmation.
    """
    message = await request.json()
    result = apply_sns_subscription_message(message, repo)
    return {"ok": True, "result": result}


@router.post("/meter/hourly")
def run_hourly_metering(
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Trigger hourly metering.

    In production call this from EventBridge Scheduler, not from the public internet.
    """
    client = MarketplaceClient(settings)
    return meter_unmetered_usage(repo, client)
