from fastapi import APIRouter, Depends, HTTPException

from api.backend.auth import require_customer
from api.backend.config import Settings, get_settings
from api.backend.db import Repository, get_repo
from api.backend.models import JobStatusResponse, MarketplaceCustomer, RandomRequest
from api.backend.rng_provider import RngService

router = APIRouter(prefix="/v1", tags=["customer-rng-api"])


@router.post("/random")
def request_random_bytes(
    request: RandomRequest,
    customer: MarketplaceCustomer = Depends(require_customer),
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
):
    service = RngService(repo, settings)
    try:
        return service.handle_random_request(request, customer)
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    customer: MarketplaceCustomer = Depends(require_customer),
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
):
    service = RngService(repo, settings)
    status = service.get_job_status(job_id, customer)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.get("/usage")
def get_usage(
    customer: MarketplaceCustomer = Depends(require_customer),
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
) -> dict:
    refreshed = repo.get_customer_by_internal_id(customer.internal_customer_id) or customer
    billable_unmetered = [
        record for record in repo.list_unmetered_usage()
        if record.internal_customer_id == customer.internal_customer_id
    ]
    return {
        "customer_id": refreshed.internal_customer_id,
        "plan": refreshed.plan,
        "status": refreshed.status,
        "free_bytes_limit": refreshed.free_bytes_limit,
        "free_bytes_used": refreshed.free_bytes_used,
        "free_bytes_remaining": max(refreshed.free_bytes_limit - refreshed.free_bytes_used, 0),
        "paid_bytes_used": refreshed.paid_bytes_used,
        "unit_bytes": settings.rng_unit_bytes,
        "billable_unmetered_records": len(billable_unmetered),
        "billable_unmetered_bytes": sum(record.raw_bytes for record in billable_unmetered),
        "billable_unmetered_quantity": sum(record.quantity for record in billable_unmetered),
        "dimension": settings.aws_marketplace_dimension,
        "note": "Free-tier usage is tracked but not sent to AWS metering. Prototype uses in-memory accounting.",
    }
