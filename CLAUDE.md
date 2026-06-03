# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PadhaiWithAI** is a Django 5 school education management system built for Rajasthan government schools (initially Tonk district). It combines a hierarchical school-administration ERP with AI-powered learning tools (question paper generation, smart tutor, math solver). PostgreSQL is the production database; Windows IIS + FastCGI is the production deployment target.

## Common Commands

All commands run from `school_project/` (the Django project root), not the repo root.

```powershell
# Run dev server
python manage.py runserver

# Migrations
python manage.py makemigrations school_app
python manage.py migrate
python manage.py migrate school_app 0026                  # apply specific migration
python manage.py migrate school_app 0025 --fake           # mark as applied without running

# Tests (Django test runner, NOT pytest)
python manage.py test school_app --verbosity=2
python manage.py test school_app.tests.ClassName.test_method_name

# Static files (required after editing JS/CSS — IIS serves from staticfiles/)
python manage.py collectstatic --noinput

# PostgreSQL shell
python manage.py dbshell

# Create superuser (idempotent — defined in management/commands/makesuperuser.py)
python manage.py makesuperuser

# DB backup to Dropbox (django-dbbackup)
python manage.py dbbackup
python manage.py backup_db                                # custom wrapper

# Quick git push (from repo root, PowerShell)
.\gpush.ps1 "commit message"                              # auto-timestamps if no msg given
```

After editing **any** static asset (JS/CSS/images), run `collectstatic` — `STATICFILES_DIRS` lists `school_app/static` and `school_app/content`, both collected to `staticfiles/` for IIS to serve. Browser cache also bites — hard-refresh (Ctrl+Shift+R) when verifying.

## Architecture

### Five-level user hierarchy

The system's organising principle. **Everything** — dashboards, permissions, data scoping — flows from this:

```
System Admin → State → District (Collector) → Block → School → Student
```

`CustomUser` (in [models.py](school_project/school_app/models.py)) has boolean role flags: `is_system_admin`, `is_state_user`, `is_district_user`, `is_block_user`, `is_school_user`. Each level's admin user is linked to its scope via a `OneToOneField` (e.g. `District.admin → CustomUser`).

**`get_user_hierarchy(user)`** in [views/hierarchy.py](school_project/school_app/views/hierarchy.py) is the canonical way to scope querysets — it returns `{state, districts, blocks, schools, students, role}` filtered to what the user can see. Views should call this rather than re-implementing the filtering logic.

Student authentication is separate from `CustomUser`: students log in via the `Student` model with roll number + password (see `student_login` view).

### Views package layout

[school_app/views/](school_project/school_app/views/) is a **package, not a single file**. [`__init__.py`](school_project/school_app/views/__init__.py) re-exports everything from each submodule so `urls.py` can keep writing `views.foo` regardless of which file `foo` lives in.

When adding a new view: place it in the topical submodule (e.g. attendance work → `attendance.py`, AI tutor → `chat.py`). [`utils.py`](school_project/school_app/views/utils.py) is the shared bag — all common imports (Django, models, forms, pandas) and helpers (`rate_limit`, `logger`) live there; every other view file does `from .utils import *`.

| Submodule | Responsibility |
|---|---|
| `auth.py` | Login, logout, captcha, password change/expiry, account lockout |
| `dashboard.py` | All role-specific dashboards (system admin, state, collector, block, school) |
| `hierarchy.py` | `get_user_hierarchy` + scoping helpers |
| `manage.py` | CRUD for States/Districts/Blocks/Schools (shared `manage_list.html` template) |
| `content_admin.py` | AI Sathi curriculum CRUD (subjects, chapters) for state users |
| `student.py`, `student_learning.py` | Student portal (login, dashboard, practice, recommendations, doubt solver) |
| `marks.py`, `tests_views.py`, `attendance.py` | Test/marks/attendance entry and reports |
| `chat.py` | AI Sathi tutor — chat, starter questions, change-chapter, feedback |
| `question_paper.py` | AI question paper generator (Sarvam AI) + history + assignments |
| `assigned_paper.py` | Teacher assigns papers, students take, OMR grading |
| `omr.py` | OMR sheet generation, upload, image processing, marks confirmation |
| `analysis.py`, `reports.py` | Student analysis API, school/block/district reports |
| `calendar.py` | Academic calendar events |
| `admin_tools.py` | System admin school/student/marks list views |

### URL routing

All URLs live in [school_app/urls.py](school_project/school_app/urls.py) — a single flat list, no `include()` for sub-apps. New endpoints go here in the appropriate commented section (look for `# State Dashboard`, `# Student Portal URLs`, etc.).

### Security middleware

[`SecurityMiddleware`](school_project/school_app/middleware.py) (custom, listed last in `MIDDLEWARE`) enforces:
- Force password change when `must_change_password=True`
- 90-day password expiry for admin roles (state/district/block/school)
- Adds CSP, X-Content-Type-Options, X-XSS-Protection headers to every response

Admin account lockout (5 failed attempts → 30 min lock) is in [auth.py](school_project/school_app/views/auth.py). Sessions expire after 30 minutes of inactivity (`SESSION_COOKIE_AGE`).

### Templates

[templates/school_app/](school_project/school_app/templates/school_app/) is organised by topic — `dashboards/`, `manage/`, `student/`, `question_paper/`, `attendance/`, `chat/`, etc. `base.html` provides the global frame with NIC + PadhaiWithAI footer logos (both served locally — do NOT reintroduce external `raj.nic.in` URLs).

The dashboard for `/dashboard/` is `dashboards/system_admin_dashboard.html`. The route `/dashboard/` redirects role-based — system admins see system_admin_dashboard, state users → state_dashboard, district users → collector_dashboard.

### Raw SQL caveat

A few views use **raw SQL via `connection.cursor()`** rather than the ORM, primarily for:
- A PostgreSQL **view** called `student_exam_results` (it's not a Django model — used in `dashboard.py`, `collector_dashboard`, `report_dashboard` for previous-year historical exam data)
- Complex two-level aggregations (CTE for school-band performance in `collector_dashboard`)

When touching these, know that `student_exam_results` is production-only — local SQLite test setup doesn't have it. The relevant tests in `tests.py` set `client.raise_request_exception = False` to skip the resulting error.

### AI integration

Three providers, all called from views:
- **Sarvam AI** (`sarvamai` SDK) — Hindi-capable; used in `question_paper.py`, `chat.py` (AI Sathi)
- **OpenAI** (`openai` SDK) — math solver in `math_utils.py`
- **Google Generative AI** (`google-generativeai`) — alternative models

When AI returns malformed JSON (a real issue with Sarvam on long prompts), use the `_repair_json()` + `call_ai_robust()` pattern in [question_paper.py](school_project/school_app/views/question_paper.py) — per-section retry, never let one bad call kill the whole paper.

**Important prompt rule**: never use `"..."` as a placeholder in JSON example structures sent to Sarvam — the model copies the dots literally. Use descriptive text like `"actual exam question text"` and append a `NO_DOTS` instruction.

### Settings highlights

- Database: `DATABASE_URL` env var (PostgreSQL) — falls back to a local default in [settings.py](school_project/school_project/settings.py) line 111
- Two `.env` files loaded in order: `school_project/.env` (overrides) then `school_app/.env` (defaults, `overwrite=False`)
- `SECRET_KEY` must be set or app crashes at startup (no default)
- `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` default to `not DEBUG` — override to `False` in `.env` for local HTTP testing
- `DBBACKUP_STORAGE` is Dropbox — requires `DROPBOX_ACCESS_TOKEN`
- `AI_SATHI_MSG_LIMIT` (default 20), `AI_SATHI_SESSION_MINS` (default 30) are tunable per env

## Working Conventions

- **No raw `print()` for debugging in committed code** — use `logger` from `views/utils.py` (`logger = logging.getLogger(__name__)`). The `school_app` logger is wired to console at INFO.
- **`{% load static %}`** is required in any template that uses `{% static %}`. The `base.html` and most dashboards already load it.
- **Migrations 0011–0025** were applied manually to production DB before migration tracking was set up. If `migrate` complains about a column existing, use `migrate school_app NNNN --fake` to register without re-running.
- **Theme tokens** are in [THEME_GUIDE.md](THEME_GUIDE.md) — primary teal `#14B8A6`, but dashboards use a blue gradient `#1e3c72 → #2a5298` (state/collector pages) and purple `#6d28d9 → #7c3aed` (chapter management). Match the existing palette for the section you're editing.
- **Excel uploads** use `pandas` + `openpyxl` for student/user bulk imports — sample files at `download_sample_school_excel` and `download_sample_student_excel` routes.

## Deployment

Production runs on **Windows IIS** with FastCGI (see [web.config](web.config)) — `wfastcgi` is in requirements.txt for this reason. `whitenoise` serves static files. `gunicorn` is also configured (see [run.sh](run.sh)) for non-Windows targets.
