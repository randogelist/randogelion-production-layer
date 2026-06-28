from fastapi import APIRouter, Depends

from api.backend.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {"ok": True, "service": settings.app_name, "env": settings.app_env}


@router.get("/v1/health")
def v1_health(settings: Settings = Depends(get_settings)) -> dict:
    return {"ok": True, "service": settings.app_name}
