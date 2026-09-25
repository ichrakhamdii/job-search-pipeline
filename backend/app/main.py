from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.api import api_router
from .core.config import settings

app = FastAPI(title="Job Search Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
