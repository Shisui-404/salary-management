"""FastAPI application factory: CORS, routers, and the domain-error -> HTTP
response mapping (see `core/errors.py`).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.api.v1.routers import health
from app.core.config import get_settings
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ACME Salary Management API",
        version="1.0.0",
        description="Employee directory, effective-dated salary history and "
        "multi-currency compensation analytics for ACME's HR team.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(api_router)
    # Also expose an unversioned /health for infra/container health checks
    # (Docker HEALTHCHECK, load balancers) that conventionally probe a fixed
    # path outside any API version prefix. `/api/v1/health` remains the
    # contract endpoint.
    app.include_router(health.router)

    return app


app = create_app()
