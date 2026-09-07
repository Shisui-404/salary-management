"""Static reference data used by the seed generator: countries, currencies,
departments, job roles (with a department and a base L1 salary), levels, and
name pools. Kept separate from `seed.py` so the generator logic is easy to
read on its own.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

# The seed is fully deterministic and must not depend on wall-clock time —
# using `date.today()` would make "byte-identical output every run" false
# the moment the calendar rolls over. Every relative date (hire dates, raise
# effective dates, currency rate `valid_from`) is anchored to this fixed date.
REFERENCE_DATE = dt.date(2025, 6, 1)
RATES_VALID_FROM = dt.date(2024, 1, 1)

RNG_SEED = 20240601


@dataclass(frozen=True)
class CountryDef:
    name: str
    code: str
    currency: str
    rate_to_base: str  # decimal string; 1 unit of `currency` = this many BASE_CURRENCY units
    weight: float  # relative headcount share
    cost_of_living: float  # multiplier applied to the USD band mid before conversion


COUNTRIES: list[CountryDef] = [
    CountryDef("United States", "US", "USD", "1.00", 0.28, 1.00),
    CountryDef("India", "IN", "INR", "0.012", 0.22, 0.35),
    CountryDef("United Kingdom", "GB", "GBP", "1.27", 0.12, 0.85),
    CountryDef("Germany", "DE", "EUR", "1.08", 0.12, 0.80),
    CountryDef("Canada", "CA", "CAD", "0.74", 0.10, 0.78),
    CountryDef("Australia", "AU", "AUD", "0.66", 0.06, 0.82),
    CountryDef("Singapore", "SG", "SGD", "0.74", 0.05, 0.88),
    CountryDef("Japan", "JP", "JPY", "0.0068", 0.05, 0.72),
]

DEPARTMENTS: list[str] = [
    "Engineering",
    "Product",
    "Sales",
    "Marketing",
    "Finance",
    "Human Resources",
    "Operations",
    "Customer Support",
    "Legal",
]

# Relative headcount weight per department (index-aligned with DEPARTMENTS).
DEPARTMENT_WEIGHTS: list[float] = [0.30, 0.08, 0.16, 0.08, 0.08, 0.06, 0.10, 0.10, 0.04]


@dataclass(frozen=True)
class JobRoleDef:
    name: str
    department: str
    base_mid_usd: int  # L1 (rank 1) band midpoint, in whole USD


JOB_ROLES: list[JobRoleDef] = [
    JobRoleDef("Software Engineer", "Engineering", 75_000),
    JobRoleDef("DevOps Engineer", "Engineering", 82_000),
    JobRoleDef("QA Engineer", "Engineering", 65_000),
    JobRoleDef("Engineering Manager", "Engineering", 135_000),
    JobRoleDef("Product Manager", "Product", 95_000),
    JobRoleDef("Product Designer", "Product", 80_000),
    JobRoleDef("Sales Representative", "Sales", 55_000),
    JobRoleDef("Account Executive", "Sales", 70_000),
    JobRoleDef("Sales Manager", "Sales", 112_000),
    JobRoleDef("Marketing Specialist", "Marketing", 55_000),
    JobRoleDef("Content Strategist", "Marketing", 60_000),
    JobRoleDef("Marketing Manager", "Marketing", 96_000),
    JobRoleDef("Financial Analyst", "Finance", 65_000),
    JobRoleDef("Accountant", "Finance", 58_000),
    JobRoleDef("Finance Manager", "Finance", 112_000),
    JobRoleDef("HR Generalist", "Human Resources", 55_000),
    JobRoleDef("Recruiter", "Human Resources", 58_000),
    JobRoleDef("HR Manager", "Human Resources", 96_000),
    JobRoleDef("Operations Analyst", "Operations", 60_000),
    JobRoleDef("Operations Manager", "Operations", 102_000),
    JobRoleDef("Customer Support Representative", "Customer Support", 42_000),
    JobRoleDef("Customer Support Lead", "Customer Support", 60_000),
    JobRoleDef("Legal Counsel", "Legal", 122_000),
]

# Level rank 1 (junior) .. 6 (executive/staff+). Each level scales a role's
# L1 band mid by this factor; ~28% growth per level compounds to roughly
# 3.4x by L6, a plausible junior-to-senior/staff spread.
LEVELS: list[tuple[str, int]] = [
    ("L1", 1),
    ("L2", 2),
    ("L3", 3),
    ("L4", 4),
    ("L5", 5),
    ("L6", 6),
]
LEVEL_GROWTH_FACTOR = 1.28

# Pyramid-shaped headcount distribution across levels (index-aligned with LEVELS).
LEVEL_WEIGHTS: list[float] = [0.12, 0.26, 0.28, 0.19, 0.11, 0.04]

BAND_MIN_FACTOR = 0.82
BAND_MAX_FACTOR = 1.28

GENDER_WEIGHTS: dict[str, float] = {
    "female": 0.46,
    "male": 0.46,
    "non_binary": 0.04,
    "undisclosed": 0.04,
}

EMPLOYMENT_STATUS_WEIGHTS: dict[str, float] = {
    "active": 0.94,
    "on_leave": 0.03,
    "terminated": 0.03,
}

FIRST_NAMES_FEMALE = [
    "Ada",
    "Grace",
    "Hedy",
    "Katherine",
    "Margaret",
    "Radia",
    "Barbara",
    "Frances",
    "Shafi",
    "Annie",
    "Sophie",
    "Elena",
    "Priya",
    "Aisha",
    "Mei",
    "Noor",
    "Isabella",
    "Chiara",
    "Yuki",
    "Fatima",
    "Olga",
    "Ingrid",
    "Camila",
    "Naomi",
    "Zoe",
    "Leila",
    "Anastasia",
    "Ravindra",
    "Meera",
    "Wanjiru",
    "Amara",
    "Freya",
    "Sana",
    "Ines",
    "Lucia",
    "Nadia",
    "Tessa",
    "Wei",
    "Yasmin",
    "Bianca",
]
FIRST_NAMES_MALE = [
    "Alan",
    "Linus",
    "Dennis",
    "Guido",
    "James",
    "Ken",
    "John",
    "Claude",
    "Edsger",
    "Donald",
    "Bjarne",
    "Vint",
    "Tim",
    "Larry",
    "Sergey",
    "Elon",
    "Satya",
    "Sundar",
    "Arjun",
    "Kwame",
    "Hiro",
    "Omar",
    "Diego",
    "Lucas",
    "Mateus",
    "Ravi",
    "Wei",
    "Chen",
    "Ahmed",
    "Ibrahim",
    "Kofi",
    "Erik",
    "Lars",
    "Mikael",
    "Jonas",
    "Pieter",
    "Andrei",
    "Dmitri",
    "Marco",
    "Giulio",
]
FIRST_NAMES_NEUTRAL = [
    "Alex",
    "Jordan",
    "Taylor",
    "Morgan",
    "Casey",
    "Riley",
    "Sam",
    "Jamie",
    "Avery",
    "Quinn",
    "Rowan",
    "Skyler",
    "Reese",
    "Emerson",
    "Finley",
    "Dakota",
]
LAST_NAMES = [
    "Lovelace",
    "Torvalds",
    "Ritchie",
    "Van Rossum",
    "Gosling",
    "Thompson",
    "Backus",
    "Hopper",
    "Lamport",
    "Knuth",
    "Berners-Lee",
    "Cerf",
    "Hamilton",
    "Page",
    "Nadella",
    "Pichai",
    "Musk",
    "Bezos",
    "Sharma",
    "Patel",
    "Kumar",
    "Singh",
    "Reddy",
    "Iyer",
    "Nakamura",
    "Tanaka",
    "Suzuki",
    "Kimura",
    "Wang",
    "Li",
    "Zhang",
    "Chen",
    "Liu",
    "Mueller",
    "Schmidt",
    "Fischer",
    "Weber",
    "Wagner",
    "Rossi",
    "Ferrari",
    "Bianchi",
    "Silva",
    "Santos",
    "Costa",
    "Pereira",
    "Almeida",
    "Dubois",
    "Bernard",
    "Moreau",
    "Kowalski",
    "Nowak",
    "Kim",
    "Park",
    "Choi",
    "Okafor",
    "Mensah",
    "Diallo",
    "Haile",
    "Larsen",
    "Nilsson",
    "Andersen",
    "Novak",
    "Popescu",
    "Ivanov",
    "Petrov",
    "Smirnov",
    "Garcia",
    "Martinez",
    "Lopez",
    "Gonzalez",
    "Rodriguez",
    "Khan",
    "Ali",
    "Hussain",
]
