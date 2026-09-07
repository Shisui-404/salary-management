"""Employee endpoints: directory list/search/filter/sort/paginate, detail,
create/update, salary history + revision, and CSV export/import.

Route ordering matters here: `/employees/export` and `/employees/import`
must be declared before `/employees/{employee_id}` so FastAPI doesn't try to
parse "export"/"import" as an integer path parameter.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import Response

from app.core.config import get_settings
from app.core.errors import EmployeeNotFoundError
from app.db.session import DbSession
from app.repositories import currency_repo, employee_repo
from app.schemas.common import Page
from app.schemas.csv_import import ImportResult, ImportRowError
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate
from app.schemas.filters import EmployeeFilterParams, EmployeeListParams
from app.schemas.salary import SalaryCreateIn, SalaryHistoryOut, SalaryRecordOut
from app.services import csv_io, employee_service, salary_service

router = APIRouter(tags=["employees"])


@router.get("/employees", response_model=Page[EmployeeOut])
def list_employees(
    params: Annotated[EmployeeListParams, Query()],
    db: DbSession,
) -> Page[EmployeeOut]:
    stmt, expr = employee_repo.build_employee_query()
    stmt = employee_repo.apply_filters(stmt, expr, params)
    total = employee_repo.count_matching(db, stmt)
    stmt = employee_repo.apply_sort(stmt, expr, params.sort)
    stmt = stmt.limit(params.limit).offset(params.offset)
    rows = db.execute(stmt).all()
    items = [employee_service.row_to_employee_out(row) for row in rows]
    return Page[EmployeeOut](items=items, total=total, limit=params.limit, offset=params.offset)


@router.get("/employees/export")
def export_employees(
    params: Annotated[EmployeeFilterParams, Query()],
    db: DbSession,
) -> Response:
    stmt, expr = employee_repo.build_employee_query()
    stmt = employee_repo.apply_filters(stmt, expr, params)
    stmt = employee_repo.apply_sort(stmt, expr, "name")
    csv_text = csv_io.export_csv(db, stmt)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@router.post("/employees/import", response_model=ImportResult)
async def import_employees(
    file: Annotated[UploadFile, File()],
    db: DbSession,
) -> ImportResult:
    content = await file.read()
    result = csv_io.import_csv(db, content)
    return ImportResult(
        total_rows=result.total_rows,
        created=result.created,
        updated=result.updated,
        failed=result.failed,
        errors=[ImportRowError(row=e.row, field=e.field, message=e.message) for e in result.errors],
    )


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: DbSession) -> EmployeeOut:
    return employee_service.get_employee_out(db, employee_id)


@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(data: EmployeeCreate, db: DbSession) -> EmployeeOut:
    return employee_service.create_employee(db, data)


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, data: EmployeeUpdate, db: DbSession) -> EmployeeOut:
    return employee_service.update_employee(db, employee_id, data)


@router.get("/employees/{employee_id}/salary-history", response_model=SalaryHistoryOut)
def get_salary_history(employee_id: int, db: DbSession) -> SalaryHistoryOut:
    if employee_repo.get_employee_or_none(db, employee_id) is None:
        raise EmployeeNotFoundError(employee_id)

    base_currency = get_settings().base_currency
    rates = currency_repo.get_all_latest_rates(db)
    pairs = salary_service.get_salary_history_with_change_pct(db, employee_id)
    items = [
        salary_service.to_salary_record_out(record, change_pct, rates, base_currency)
        for record, change_pct in pairs
    ]
    return SalaryHistoryOut(items=items)


@router.post(
    "/employees/{employee_id}/salary",
    response_model=SalaryRecordOut,
    status_code=status.HTTP_201_CREATED,
)
def create_salary_record(employee_id: int, data: SalaryCreateIn, db: DbSession) -> SalaryRecordOut:
    salary_service.record_salary_change(
        db,
        employee_id=employee_id,
        amount=data.amount,
        currency=data.currency,
        effective_from=data.effective_from,
        change_reason=data.change_reason,
        note=data.note,
    )
    db.commit()

    base_currency = get_settings().base_currency
    rates = currency_repo.get_all_latest_rates(db)
    newest_record, change_pct = salary_service.get_salary_history_with_change_pct(db, employee_id)[
        0
    ]
    return salary_service.to_salary_record_out(newest_record, change_pct, rates, base_currency)
