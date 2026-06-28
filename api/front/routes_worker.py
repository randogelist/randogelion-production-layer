from fastapi import APIRouter, Depends, HTTPException

from api.backend.auth import require_worker
from api.backend.config import Settings, get_settings
from api.backend.db import Repository, get_repo
from api.backend.models import WorkerClaimResponse, WorkerCompleteRequest
from api.backend.rng_provider import RngService, get_embedded_magazine_status
from api.backend.storage import ObjectStorage

router = APIRouter(prefix="/internal/worker", tags=["internal-worker"])


@router.get("/magazine/status")
def magazine_status(
    worker_id: str = Depends(require_worker),
    settings: Settings = Depends(get_settings),
):
    return get_embedded_magazine_status(settings)


@router.get("/jobs/next", response_model=WorkerClaimResponse)
def claim_next_job(
    worker_id: str = Depends(require_worker),
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
):
    storage = ObjectStorage(settings)
    placeholder_key = "rng-output/pending.bin"
    job = repo.claim_next_job(worker_id=worker_id, s3_key=placeholder_key)

    if not job:
        return WorkerClaimResponse(message="no job available")

    s3_key = storage.make_job_output_key(job.job_id)
    job.output_s3_key = s3_key
    upload_url = storage.presign_upload(s3_key)

    return WorkerClaimResponse(
        job_id=job.job_id,
        request_id=job.request_id,
        bytes=job.requested_bytes,
        s3_bucket=settings.s3_bucket,
        s3_key=s3_key,
        message=upload_url or "upload URL unavailable; upload via AWS SDK and then complete the job",
    )


@router.post("/jobs/{job_id}/complete")
def complete_job(
    job_id: str,
    body: WorkerCompleteRequest,
    worker_id: str = Depends(require_worker),
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
):
    service = RngService(repo, settings)
    job = service.complete_worker_job(job_id, body.s3_key, body.bytes, body.sha256)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"ok": True, "job_id": job.job_id, "status": job.status, "claimed_by": job.claimed_by}


@router.post("/jobs/{job_id}/fail")
def fail_job(
    job_id: str,
    reason: dict,
    worker_id: str = Depends(require_worker),
    repo: Repository = Depends(get_repo),
):
    job = repo.fail_job(job_id, reason.get("error", "worker failed"))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"ok": True, "job_id": job.job_id, "status": job.status}
