"""`GET /health` — liveness plus a trivial DB round-trip and row count."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.db.session import DbSession
from app.models.employee import Employee

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: DbSession) -> dict:
    try:
        employee_count = db.execute(select(func.count()).select_from(Employee)).scalar_one()
        database_status = "ok"
    except Exception:
        employee_count = 0
        database_status = "error"

    return {
        "status": "ok" if database_status == "ok" else "degraded",
        "database": database_status,
        "employee_count": employee_count,
    }
