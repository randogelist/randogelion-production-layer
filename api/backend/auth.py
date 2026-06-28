import secrets
from fastapi import Depends, Header, HTTPException, status

from api.backend.config import Settings, get_settings
from api.backend.db import Repository, get_repo, hash_api_key
from api.backend.models import CustomerStatus, MarketplaceCustomer


def issue_plain_api_key() -> str:
    return f"rng_live_{secrets.token_urlsafe(32)}"


def create_customer_api_key(customer: MarketplaceCustomer, repo: Repository, settings: Settings) -> str:
    plain = issue_plain_api_key()
    repo.create_api_key(
        internal_customer_id=customer.internal_customer_id,
        api_key_hash=hash_api_key(plain, settings.api_key_pepper),
    )
    return plain


def require_customer(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
) -> MarketplaceCustomer:
    token = x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    record = repo.find_api_key_hash(hash_api_key(token, settings.api_key_pepper))
    if not record or record.disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    customer = repo.get_customer_by_internal_id(record.internal_customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Customer not found")
    if customer.status != CustomerStatus.active and not settings.local_dev_allow_fake_marketplace:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Subscription is not active")
    return customer


def require_worker(
    x_worker_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    if not x_worker_token or not secrets.compare_digest(x_worker_token, settings.worker_shared_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid worker token")
    return "local-worker"
