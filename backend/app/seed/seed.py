"""Deterministic seed generator for the ACME salary-management database.

    python -m app.seed.seed --count 10000 [--reset]

Everything here is driven by a single `random.Random(RNG_SEED)` instance
consumed in a fixed order, and every date is anchored to a fixed
`data.REFERENCE_DATE` rather than `date.today()` — so two runs with the same
`--count` produce byte-identical rows, which is what makes the test suite
and any manual verification reproducible.

**Two deliberate signals are injected into the generated data, on purpose,
so the analytics screens (`/analytics/pay-equity`, `/analytics/band-health`)
have something real to show rather than a flat, uninteresting dataset:**

1. **A small, systematic gender pay gap.** Female employees' salaries are
   drawn from a distribution shifted `GENDER_GAP_PCT` (4%) below male
   employees' in the same (job role, level, country) cell, before the
   per-employee noise is added. This is intentionally small enough to
   require a real statistical view (median-within-cell, sample-size guard)
   to detect reliably — exactly the kind of gap the pay-equity endpoint
   exists to surface, not a gross, obvious outlier.
2. **A handful of out-of-band outliers.** `OUTLIER_RATE` (1.5%) of
   employees get their computed salary pushed below their band's `min` or
   above its `max` (chosen independently of the gender-gap shift), so
   `/analytics/band-health` has a genuine, non-empty outlier list to rank
   instead of an all-`within` dataset.

Both are seeded from the same deterministic RNG, so they reproduce exactly
across runs — they are data-generation choices, not bugs to "fix" if a
consumer of this data notices them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import time
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, insert, select

from app.db.session import Base, SessionLocal, engine
from app.models.currency_rate import CurrencyRate
from app.models.employee import Employee
from app.models.reference import Country, Department, JobRole, Level
from app.models.salary_band import SalaryBand
from app.models.salary_record import SalaryRecord
from app.seed import data

BATCH_SIZE = 2000
GENDER_GAP_PCT = Decimal("0.04")
OUTLIER_RATE = 0.015
OUTLIER_BELOW_FACTOR = Decimal("0.65")
OUTLIER_ABOVE_FACTOR = Decimal("1.55")
SALARY_NOISE_STDDEV_PCT = 0.10  # per-employee dispersion around the (gap-adjusted) band mid

RAISE_REASONS = ["annual_review", "annual_review", "promotion", "market_adjustment"]


def _weighted_choice(rng: random.Random, items: list, weights: list[float]):
    return rng.choices(items, weights=weights, k=1)[0]


def _round_2dp(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_minor(value: Decimal) -> int:
    return int(_round_2dp(value) * 100)


def _random_normal_pct(
    rng: random.Random, mean: float, stddev: float, lo: float, hi: float
) -> float:
    return max(lo, min(hi, rng.gauss(mean, stddev)))


def seed(count: int, reset: bool) -> None:
    t_start = time.perf_counter()
    rng = random.Random(data.RNG_SEED)

    if reset:
        print("Dropping existing tables...")
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        existing = db.execute(select(func.count()).select_from(Employee)).scalar_one()
        if existing and not reset:
            print(f"Database already has {existing} employees; pass --reset to wipe and reseed.")
            return

        print(f"Seeding {count} employees (RNG seed={data.RNG_SEED}, reset={reset})...")

        # ---- Reference data -------------------------------------------------
        departments = {name: Department(name=name) for name in data.DEPARTMENTS}
        db.add_all(departments.values())

        job_roles = {r.name: JobRole(name=r.name) for r in data.JOB_ROLES}
        db.add_all(job_roles.values())

        levels = {name: Level(name=name, rank=rank) for name, rank in data.LEVELS}
        db.add_all(levels.values())

        countries = {
            c.name: Country(name=c.name, code=c.code, currency=c.currency) for c in data.COUNTRIES
        }
        db.add_all(countries.values())

        db.flush()  # assign ids

        for c in data.COUNTRIES:
            db.add(
                CurrencyRate(
                    currency=c.currency,
                    rate_to_base=Decimal(c.rate_to_base),
                    valid_from=data.RATES_VALID_FROM,
                )
            )
        rate_to_base_by_currency = {c.currency: Decimal(c.rate_to_base) for c in data.COUNTRIES}

        # band mid (USD) per (job_role, level, country), scaled by level growth
        # and the country's cost-of-living multiplier.
        band_mid_usd: dict[tuple[str, str, str], Decimal] = {}
        for role in data.JOB_ROLES:
            for level_name, rank in data.LEVELS:
                growth = Decimal(str(data.LEVEL_GROWTH_FACTOR)) ** (rank - 1)
                base_mid = Decimal(role.base_mid_usd) * growth
                for c in data.COUNTRIES:
                    mid = base_mid * Decimal(str(c.cost_of_living))
                    band_mid_usd[(role.name, level_name, c.name)] = mid

        for (role_name, level_name, country_name), mid in band_mid_usd.items():
            mid_minor = _to_minor(mid)
            db.add(
                SalaryBand(
                    job_role_id=job_roles[role_name].id,
                    level_id=levels[level_name].id,
                    country_id=countries[country_name].id,
                    min_minor=_to_minor(mid * Decimal(str(data.BAND_MIN_FACTOR))),
                    mid_minor=mid_minor,
                    max_minor=_to_minor(mid * Decimal(str(data.BAND_MAX_FACTOR))),
                    currency="USD",
                )
            )
        db.commit()
        print(
            f"  reference data: {len(departments)} departments, {len(job_roles)} job roles, "
            f"{len(levels)} levels, {len(countries)} countries, "
            f"{len(band_mid_usd)} salary bands"
        )

        # ---- Employees + salary history --------------------------------------
        dept_names = list(departments)
        roles_by_department: dict[str, list[data.JobRoleDef]] = {}
        for role in data.JOB_ROLES:
            roles_by_department.setdefault(role.department, []).append(role)

        country_names = [c.name for c in data.COUNTRIES]
        country_weights = [c.weight for c in data.COUNTRIES]
        level_names = [name for name, _rank in data.LEVELS]

        gender_names = list(data.GENDER_WEIGHTS)
        gender_weights = list(data.GENDER_WEIGHTS.values())
        status_names = list(data.EMPLOYMENT_STATUS_WEIGHTS)
        status_weights = list(data.EMPLOYMENT_STATUS_WEIGHTS.values())

        used_emails: set[str] = set()
        employee_rows: list[dict] = []
        # per-department, per-level-rank list of already-generated employee ids,
        # used to assign a plausible manager (someone senior, same department).
        dept_level_pool: dict[str, dict[int, list[int]]] = {name: {} for name in dept_names}

        for emp_id in range(1, count + 1):
            department = _weighted_choice(rng, dept_names, data.DEPARTMENT_WEIGHTS)
            role = rng.choice(roles_by_department[department])
            level_name = _weighted_choice(rng, level_names, data.LEVEL_WEIGHTS)
            level_rank = dict(data.LEVELS)[level_name]
            country_name = _weighted_choice(rng, country_names, country_weights)
            gender = _weighted_choice(rng, gender_names, gender_weights)
            status = _weighted_choice(rng, status_names, status_weights)

            if gender == "female":
                first_name = rng.choice(data.FIRST_NAMES_FEMALE)
            elif gender == "male":
                first_name = rng.choice(data.FIRST_NAMES_MALE)
            else:
                first_name = rng.choice(data.FIRST_NAMES_NEUTRAL)
            last_name = rng.choice(data.LAST_NAMES)

            local_part = f"{first_name}.{last_name}".lower().replace(" ", "-").replace("'", "")
            email = f"{local_part}@acme.com"
            suffix = 1
            while email in used_emails:
                suffix += 1
                email = f"{local_part}{suffix}@acme.com"
            used_emails.add(email)

            hire_days_ago = rng.randint(30, 10 * 365)
            hire_date = data.REFERENCE_DATE - dt.timedelta(days=hire_days_ago)

            manager_id = None
            senior_pool: list[int] = []
            for r in (level_rank + 1, level_rank + 2):
                senior_pool.extend(dept_level_pool[department].get(r, []))
            if senior_pool and rng.random() < 0.85:
                manager_id = rng.choice(senior_pool)

            dept_level_pool[department].setdefault(level_rank, []).append(emp_id)

            employee_rows.append(
                {
                    "id": emp_id,
                    "employee_code": f"ACME-{emp_id:06d}",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "gender": gender,
                    "hire_date": hire_date,
                    "employment_status": status,
                    "department_id": departments[department].id,
                    "job_role_id": job_roles[role.name].id,
                    "level_id": levels[level_name].id,
                    "country_id": countries[country_name].id,
                    "manager_id": manager_id,
                    "_role_name": role.name,
                    "_level_name": level_name,
                    "_country_name": country_name,
                    "_gender": gender,
                    "_hire_date": hire_date,
                }
            )

        elapsed_gen = time.perf_counter() - t_start
        print(f"  generated {len(employee_rows)} employee rows in {elapsed_gen:.2f}s")

        # ---- Salary history ---------------------------------------------------
        salary_rows: list[dict] = []
        for row in employee_rows:
            mid_usd = band_mid_usd[(row["_role_name"], row["_level_name"], row["_country_name"])]
            country_currency = next(
                c.currency for c in data.COUNTRIES if c.name == row["_country_name"]
            )
            rate = rate_to_base_by_currency[country_currency]

            gap_multiplier = (
                Decimal("1") - GENDER_GAP_PCT if row["_gender"] == "female" else Decimal("1")
            )
            noise_pct = _random_normal_pct(rng, 0.0, SALARY_NOISE_STDDEV_PCT, -0.30, 0.30)
            base_local_mid = (mid_usd * gap_multiplier) / rate
            amount = base_local_mid * (Decimal("1") + Decimal(str(noise_pct)))

            if rng.random() < OUTLIER_RATE:
                amount *= OUTLIER_BELOW_FACTOR if rng.random() < 0.5 else OUTLIER_ABOVE_FACTOR

            amount = max(amount, Decimal("1"))
            effective_from = row["_hire_date"]
            n_records = _weighted_choice(rng, [1, 2, 3, 4], [0.30, 0.35, 0.24, 0.11])

            record_id_start = len(salary_rows)
            for i in range(n_records):
                reason = "initial" if i == 0 else rng.choice(RAISE_REASONS)
                salary_rows.append(
                    {
                        "employee_id": row["id"],
                        "amount_minor": _to_minor(amount),
                        "currency": country_currency,
                        "effective_from": effective_from,
                        "effective_to": None,
                        "change_reason": reason,
                        "note": None,
                    }
                )
                if i < n_records - 1:
                    gap_days = rng.randint(300, 540)
                    next_from = effective_from + dt.timedelta(days=gap_days)
                    if next_from >= data.REFERENCE_DATE:
                        break
                    salary_rows[record_id_start + i]["effective_to"] = next_from - dt.timedelta(
                        days=1
                    )
                    raise_pct = _random_normal_pct(rng, 0.06, 0.03, 0.0, 0.20)
                    amount = amount * (Decimal("1") + Decimal(str(raise_pct)))
                    effective_from = next_from

        print(f"  generated {len(salary_rows)} salary records")

        # ---- Bulk insert --------------------------------------------------
        employee_table_rows = [
            {k: v for k, v in row.items() if not k.startswith("_")} for row in employee_rows
        ]
        _bulk_insert(db, Employee.__table__, employee_table_rows)
        _bulk_insert(db, SalaryRecord.__table__, salary_rows)
        db.commit()

    elapsed = time.perf_counter() - t_start
    print(f"Done in {elapsed:.2f}s: {count} employees, {len(salary_rows)} salary records.")


def _bulk_insert(db, table, rows: list[dict]) -> None:
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        db.execute(insert(table), batch)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10_000, help="number of employees to generate")
    parser.add_argument(
        "--reset", action="store_true", help="drop and recreate all tables before seeding"
    )
    args = parser.parse_args()
    seed(args.count, args.reset)


if __name__ == "__main__":
    main()
