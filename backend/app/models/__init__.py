"""Import every model module so `Base.metadata` is fully populated and all
inter-model relationships (declared by string class name) resolve, no matter
which module happens to import `app.models` first.
"""

from app.models.currency_rate import CurrencyRate
from app.models.employee import Employee
from app.models.reference import Country, Department, JobRole, Level
from app.models.salary_band import SalaryBand
from app.models.salary_record import SalaryRecord

__all__ = [
    "Country",
    "CurrencyRate",
    "Department",
    "Employee",
    "JobRole",
    "Level",
    "SalaryBand",
    "SalaryRecord",
]
