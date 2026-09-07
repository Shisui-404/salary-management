# ADR-004: No migrations tool — `create_all` plus the seed script

## Context
A migrations framework (Alembic) earns its keep when a schema evolves across
environments with existing data that must be preserved and transformed
release-to-release. This project is a fresh assessment build: there is no
production database with real data to migrate, and the schema is defined once
by the SQLAlchemy models before any deployment.

## Decision
`Base.metadata.create_all(engine)` creates the schema from the current model
definitions — called by both the app's own startup path (implicitly, via the
first session) and explicitly at the top of `seed/seed.py`. There is no
`alembic/` directory, no migration files, no version table. `--reset` on the
seed script (`Base.metadata.drop_all` then `create_all`) is the reset path for
local development and for `docker-compose up` bringing up a fresh Postgres
volume.

## Consequences
- Zero migration-framework ceremony (no `alembic.ini`, no autogenerate review,
  no migration-file drift from the models) for a project with no real
  deployment history to reconcile.
- Changing a model's shape mid-development just means dropping and re-seeding
  — appropriate for this project's stage, not for a live production system.
- This is explicitly called out as the first thing to add before any real
  production deployment (alongside auth — see requirements.md §4): a
  production rollout needs Alembic (or equivalent) the moment there is data
  that must survive a schema change.

## Alternatives considered
- **Alembic from day one**: the standard, correct choice for a system with a
  real deployment lifecycle; deliberately deferred here because it adds
  process weight (autogenerate review, migration-file maintenance) with zero
  payoff before there is a database anyone needs to preserve.
- **Raw SQL DDL scripts**: strictly worse than `create_all` — hand-written
  DDL can drift from the ORM models it's supposed to describe; `create_all`
  cannot drift because it *is* the models.
