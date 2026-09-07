"""Assembles every v1 router under the `/api/v1` prefix."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import analytics, employees, health, reference

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(reference.router)
api_router.include_router(employees.router)
api_router.include_router(analytics.router)
