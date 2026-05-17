# Step 29 — Alembic Migrations Plan

Status: next recommended backend step after Step 28.

## Why Step 29 is needed

Planora now has a large FastAPI + SQLAlchemy + PostgreSQL backend with many tables and constraints. Until now, database changes were handled mostly through SQLAlchemy models, manual SQL, or test database recreation.

That is becoming risky because:

- Existing PostgreSQL tables do not change automatically when SQLAlchemy models change.
- Manual `ALTER TABLE` fixes are easy to forget.
- The development database, test database, and schema design file can drift apart.
- Future deployment needs a repeatable database upgrade process.

Step 29 should add Alembic so Planora has controlled, versioned database migrations.

## Goal

Add Alembic migration support without changing application behavior.

Step 29 is a structure/infrastructure step, not a feature step.

The goal is:

```txt
SQLAlchemy models
↓
Alembic migrations
↓
PostgreSQL database schema
```

## Scope

Step 29 should include:

1. Install and configure Alembic.
2. Create `alembic.ini`.
3. Create `alembic/` migration folder.
4. Configure Alembic to read the same `DATABASE_URL` from `app.core.config.settings`.
5. Configure Alembic `target_metadata = Base.metadata`.
6. Import all models so Alembic can detect tables and constraints.
7. Generate an initial baseline migration.
8. Decide whether the existing development database should be stamped or recreated.
9. Verify migration commands work.
10. Add documentation for future migration workflow.

## Important decision

Because the current Planora database already exists, Step 29 should not blindly run an initial migration against the existing dev database if it would try to recreate existing tables.

Recommended approach:

- For existing local development database: use `alembic stamp head` after confirming the schema already matches the models closely enough.
- For fresh databases: use `alembic upgrade head`.
- For test databases: tests currently recreate tables with SQLAlchemy `Base.metadata.create_all`; do not change the test strategy unless deliberately planned later.

## Files likely added

```txt
alembic.ini
alembic/env.py
alembic/script.py.mako
alembic/versions/<initial_revision>_initial_planora_schema.py
docs/STEP_29_ALEMBIC_MIGRATIONS_PLAN.md
```

## Files likely updated

```txt
requirements.txt
.env.example
docs/PLANORA_CONTEXT.md
```

Optional later updates:

```txt
tests/conftest.py
README.md
```

## Package

Add Alembic:

```powershell
python -m pip install alembic
```

Then update `requirements.txt` using the installed version.

## Configuration notes

`alembic/env.py` should import:

```python
from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401
```

Alembic should use:

```python
target_metadata = Base.metadata
```

The database URL should come from:

```python
settings.database_url
```

Do not hardcode the database password or URL inside `alembic.ini`.

## Live database caution

Before stamping or upgrading the live development database, check current database:

```sql
SELECT current_database();
```

Then verify important constraints that were previously fixed manually:

```sql
SELECT conname
FROM pg_constraint
WHERE conname IN (
    'chk_tasks_priority',
    'chk_oauth_accounts_provider',
    'chk_password_reset_codes_expiry'
);
```

Important existing fix still remembered:

```sql
ALTER TABLE password_reset_codes
DROP CONSTRAINT IF EXISTS chk_password_reset_codes_expiry;

ALTER TABLE password_reset_codes
ADD CONSTRAINT chk_password_reset_codes_expiry
CHECK (expires_at > created_at);
```

## Commands Step 29 should end with

Check Alembic current version:

```powershell
python -m alembic current
```

Create a migration after future model changes:

```powershell
python -m alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```powershell
python -m alembic upgrade head
```

Mark existing database as already matching latest migration:

```powershell
python -m alembic stamp head
```

## Testing expectations

Step 29 should not break existing backend tests.

Run:

```powershell
python -m pytest tests/test_20_firebase_push_service.py -v
python -m pytest -x -v
```

Expected current full regression baseline before Step 29:

```txt
129 passed
```

After Step 29, expected result should remain:

```txt
129 passed
```

Unless Step 29 intentionally adds new tests.

## What Step 29 should NOT do

Do not:

- Add Docker yet.
- Replace the whole database manually.
- Commit `.env` or database credentials.
- Commit Firebase service-account JSON.
- Change business logic endpoints.
- Change authentication behavior.
- Change Firebase push behavior.
- Add Firebase Storage yet.

## After Step 29

Good next candidates after Alembic:

1. Firebase Storage for attachments, if attachment storage is urgent.
2. Admin/notification polish.
3. Frontend/admin dashboard integration.
4. Mobile app integration.
5. Ruff/linting cleanup.
6. Docker/deployment polish after the system is stable.

## Success criteria

Step 29 is complete when:

- Alembic is installed and configured.
- `alembic.ini` and `alembic/` exist.
- Alembic can import all SQLAlchemy models.
- Alembic can connect using `settings.database_url`.
- A baseline migration exists.
- Existing local database can be stamped safely.
- Fresh database can be upgraded using `alembic upgrade head`.
- Full regression still passes.
- `docs/PLANORA_CONTEXT.md` is updated after completion.
