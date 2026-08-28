from app.api.v1.endpoints import analytics, datasets, plans, profiling, quality, runs
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(profiling.router, prefix="/datasets", tags=["Profiling"])
api_router.include_router(quality.router, prefix="/datasets", tags=["Quality"])
api_router.include_router(plans.router, prefix="/plans", tags=["Plans"])
api_router.include_router(runs.router, prefix="/runs", tags=["Runs"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Business Analytics"])
