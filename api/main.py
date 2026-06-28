from fastapi import FastAPI

from api.front.routes_health import router as health_router
from api.front.routes_marketplace import router as marketplace_router
from api.front.routes_rng import router as rng_router
from api.front.routes_worker import router as worker_router

app = FastAPI(
    title="AWS Marketplace RNG API Blueprint",
    version="0.1.0",
    description="Blueprint REST API for an AWS Marketplace SaaS RNG product with a local worker bridge.",
)

app.include_router(health_router)
app.include_router(marketplace_router)
app.include_router(rng_router)
app.include_router(worker_router)
