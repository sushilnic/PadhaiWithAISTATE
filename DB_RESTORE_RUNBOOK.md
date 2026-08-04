# PostgreSQL Restore Runbook — PadhaiWithAI

**Last reviewed:** 2026-07-27
**Owner:** DevOps / DBA
**Scope:** Production Postgres restore from a `dbbackup` dump

---

## Why this runbook exists

Twice in this project we have hit the same class of bug:

1. `AiSathiChatSession` table missing after a manual migration restore → student delete crashed with `UndefinedTable`
2. `QuestionPaperHistory` primary-key sequence out of sync after a restore → every insert failed with `duplicate key value violates unique constraint`

Both are symptoms of an **incomplete restore workflow**. Both are 100 % preventable if this runbook is followed.

**Golden rule:** never mark a migration as `--fake` on production unless you can explain, in writing on this document, exactly what state the database was in when you did it, and why the migration state and physical schema were already in sync.

---

## Concepts you need to hold in your head

| Term | Meaning | Why it matters |
|---|---|---|
| **Migration state** | Rows in `django_migrations` table telling Django "these have been applied" | Django only runs migrations whose row is missing |
| **Physical schema** | Actual `CREATE TABLE` / `ALTER TABLE` state of the DB | This is what your queries hit |
| **Sequence** | PostgreSQL counter that generates the next `id` for a `SERIAL`/`BIGSERIAL` column | If it lags behind `MAX(id)`, every insert crashes |
| **`--fake`** | `python manage.py migrate app N --fake` → adds the row to `django_migrations` **without running the SQL** | Only safe if the physical schema already matches |

The two bugs we hit both happened because someone did `--fake` when migration state and physical schema were **not** in sync.

---

## Restoring the production database — the correct procedure

### Prerequisites

- SSH / RDP access to the production server (or wherever `pg_restore` will run)
- The dump file (`.dump` or `.sql`) copied to that box
- Credentials for the target Postgres user in the app's `.env`
- 15 – 30 minutes of downtime window

### Step-by-step

```bash
# ─── 0. Announce the maintenance window ───────────────────────────────
# Notify block/school admins over WhatsApp: "PadhaiWithAI unavailable 22:00–22:30 IST"

# ─── 1. Stop the web layer ────────────────────────────────────────────
# On the IIS host:
iisreset /stop
# Or if using gunicorn/docker:
docker compose stop web

# ─── 2. Rename the current DB (do NOT drop — this is your rollback) ──
python manage.py dbshell -- -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database();"
psql -U postgres -c "ALTER DATABASE padhaiwithai RENAME TO padhaiwithai_pre_restore_$(date +%Y%m%d_%H%M);"
psql -U postgres -c "CREATE DATABASE padhaiwithai OWNER padhaiwithai_app;"

# ─── 3. Restore the dump ──────────────────────────────────────────────
# For .dump (custom format):
pg_restore -U padhaiwithai_app -d padhaiwithai --no-owner --no-privileges backup.dump

# For .sql (plain SQL):
psql -U padhaiwithai_app -d padhaiwithai -f backup.sql

# ─── 4. Reset ALL sequences to match the current MAX(id) — CRITICAL ─
# (see also: python manage.py restore_db --step=fix-sequences)
python manage.py sqlsequencereset school_app | python manage.py dbshell

# ─── 5. Verify migration state matches physical schema ────────────────
python manage.py showmigrations school_app | grep -v '\[X\]'
#   Any migrations shown as un-applied here must NOT be --fake'd unless
#   you have PROOF the physical tables already exist in the DB.
#   To check whether a table exists:
python manage.py dbshell -- -c "\dt school_app_*"

# ─── 6. Apply any legitimately-missing migrations ─────────────────────
python manage.py migrate school_app
# If you see "relation already exists" errors — STOP and use --fake for
# ONLY the specific migration whose tables you verified in step 5.

# ─── 7. Verify data ───────────────────────────────────────────────────
python manage.py dbshell -- -c "SELECT count(*) FROM school_app_student;"
python manage.py dbshell -- -c "SELECT count(*) FROM school_app_school;"
python manage.py dbshell -- -c "SELECT count(*) FROM school_app_marks;"
# Numbers should match what you expected from the backup source

# ─── 8. Smoke-test the app ────────────────────────────────────────────
python manage.py runserver 0.0.0.0:8080 &
curl -o /dev/null -s -w "%{http_code}\n" http://localhost:8080/login/
# Expect 200

# ─── 9. Restart the web layer ─────────────────────────────────────────
iisreset /start
# Or:
docker compose start web

# ─── 10. Keep the pre-restore DB for 7 days ──────────────────────────
# If everything works: after 7 days,
psql -U postgres -c "DROP DATABASE padhaiwithai_pre_restore_YYYYMMDD_HHMM;"
# If something is wrong: rollback,
psql -U postgres -c "ALTER DATABASE padhaiwithai RENAME TO padhaiwithai_failed_$(date +%Y%m%d_%H%M); ALTER DATABASE padhaiwithai_pre_restore_YYYYMMDD_HHMM RENAME TO padhaiwithai;"
```

---

## Automated helper — `python manage.py restore_db`

We now ship a management command that automates the safe post-restore work (sequence reset + migration verification). Use it after step 3 (or as a standalone diagnostic anytime you suspect the DB is off).

```bash
# Read-only diagnostic — always safe
python manage.py restore_db --check

# Reset all sequences to match MAX(id) — safe, idempotent
python manage.py restore_db --fix-sequences

# Run all safe post-restore steps in order
python manage.py restore_db --full
```

The command:

- Never drops data
- Never runs `--fake` (you must do that by hand, only after reading this doc)
- Prints the actual SQL it's about to run before executing
- Exits non-zero on any failure, so it's safe to chain into CI

See `school_app/management/commands/restore_db.py` for source.

---

## Common failure modes and what to do

### `duplicate key value violates unique constraint "..._pkey"`

**Cause:** Sequence out of sync — Postgres is trying `id=N` but `id=N` already exists in the table.

**Fix:**
```bash
python manage.py restore_db --fix-sequences
```

### `relation "..." does not exist`

**Cause:** A model exists in Python + a migration file exists, but the physical table was never created (usually because the migration was `--fake`'d before its `CreateModel` operation had a chance to run).

**Fix:**
```bash
# See what tables Django expects vs what exists
python manage.py restore_db --check
# For each missing table, create it via a small RunSQL migration
# (see 0031_ensure_ai_sathi_session_tables.py for a template)
```

### `column "..." does not exist`

**Cause:** An `AddField` migration was `--fake`'d without adding the column.

**Fix:**
```bash
# Manually add the column
python manage.py dbshell
ALTER TABLE <table> ADD COLUMN <name> <type>;
# Verify the migration state now matches physical
python manage.py restore_db --check
```

### `migrate` says "relation already exists"

**Cause:** Migration state says un-applied but the physical table exists. This is the classic "we restored a dump but forgot the `django_migrations` rows".

**Fix — only after confirming the physical table matches the model:**
```bash
python manage.py migrate school_app <migration_name> --fake
# Then document HERE (append to the log at the bottom of this file)
# what migration you --fake'd and why.
```

---

## What NOT to do (learned from experience)

| Don't | Why |
|---|---|
| ❌ Restore a `.dump` without running step 4 (sequence reset) | Every subsequent INSERT crashes |
| ❌ Use `--fake` because the migration "seems already applied" | If the physical schema doesn't match, later migrations will fail in confusing ways |
| ❌ Drop the pre-restore DB immediately | You lose the ability to roll back if something is wrong |
| ❌ Skip step 7 (data verification) | Silent data loss is much worse than an obvious error |
| ❌ Restore during peak hours (09:00–17:00) | Users will hit inconsistent state; do it at night |

---

## Monthly restore drill (recommended)

To keep this workflow honest, do the following once a month:

1. Copy last night's Dropbox backup to a scratch box
2. Restore into a scratch DB following the steps above
3. Run `python manage.py restore_db --check` — should print all-green
4. Run `python manage.py test school_app --settings=school_project.settings_scratch` — a subset of tests should pass
5. Drop the scratch DB

If any step fails, you have a real problem to fix **before** you need to restore in an emergency.

---

## Change log

_Append to this list whenever the runbook changes or a real restore happens._

- **2026-07-27** — Initial version. Written after the `AISathiChatSession` missing-table and `QuestionPaperHistory` sequence-out-of-sync incidents. Introduced `restore_db` management command.
