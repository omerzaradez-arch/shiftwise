# Alembic migrations

The infrastructure is wired (`alembic.ini`, `env.py`, models imported), but
historically schema changes have been made via the `COLUMN_MIGRATIONS` list in
`app/main.py` — small `ALTER TABLE ADD COLUMN IF NOT EXISTS` statements that
run at startup.

That works for adding nullable columns but **will lose data** for anything
non-trivial (renames, drops, type changes, FK changes). Time to migrate to
real Alembic versioning.

## One-time baseline (do this once, in production)

The production DB already has the current schema. We need to tell Alembic
"this is the starting point — don't try to recreate the existing tables."

```bash
# 1. SSH into Railway (or run from a local shell with DATABASE_URL pointing at prod):
cd backend
export DATABASE_URL="postgresql://...railway prod URL..."

# 2. Generate an initial migration from the current model state:
alembic revision --autogenerate -m "baseline current schema"
# Inspect the generated file in alembic/versions/ — it should match what's already in prod.

# 3. Mark this revision as already-applied (so it doesn't try to re-create tables):
alembic stamp head
```

After this, the prod DB knows it's at the baseline revision.

## Adding a new schema change

```bash
# 1. Edit the SQLAlchemy model in app/models/...
# 2. Generate a migration:
alembic revision --autogenerate -m "add foo column to employees"

# 3. Review the generated file in alembic/versions/ — autogenerate is fallible.
#    Common gotchas:
#    - It misses index renames
#    - It can't see CHECK constraint changes
#    - It writes `op.drop_column` for renamed columns instead of `op.alter_column`

# 4. Apply locally for testing:
alembic upgrade head

# 5. Commit the migration file + push. The production deploy should
#    run `alembic upgrade head` as part of its startup (see below).
```

## Wiring auto-upgrade on Railway deploy

Once the baseline is in place, replace the `COLUMN_MIGRATIONS` hack in
`app/main.py`. In the lifespan handler, instead of running raw SQL, run:

```python
from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
```

Or — safer for production — run it as a deploy hook in Railway:
**Settings → Deploy → Pre-deploy command:** `alembic upgrade head`.

That way schema migrations happen before the new app code goes live, and a
failed migration aborts the deploy without breaking the running version.

## When NOT to use Alembic

For pure data backfills (one-off scripts), prefer a dedicated `scripts/` file
that you run manually. Alembic migrations should focus on schema only.
