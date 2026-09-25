from fastapi import APIRouter

from .endpoints import auth, cv, jobs, tracking, documents

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cv.router)
api_router.include_router(jobs.router)
api_router.include_router(tracking.router)
api_router.include_router(documents.router)
