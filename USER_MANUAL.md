# PadhaiWithAI — Implementation Manual
### For New District / State Deployment

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Technology Stack & Prerequisites](#2-technology-stack--prerequisites)
3. [Installation](#3-installation)
4. [Environment Configuration](#4-environment-configuration)
5. [Database Setup](#5-database-setup)
6. [First-Time Setup: Create Hierarchy](#6-first-time-setup-create-hierarchy)
7. [User Roles Reference](#7-user-roles-reference)
8. [Student Data Upload](#8-student-data-upload)
9. [Test Management](#9-test-management)
10. [Collector (District) Dashboard](#10-collector-district-dashboard)
11. [Security & Session Settings](#11-security--session-settings)
12. [Backup Configuration](#12-backup-configuration)
13. [Production Deployment Checklist](#13-production-deployment-checklist)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. System Overview

PadhaiWithAI is a hierarchical school management and student assessment platform. It supports:

- **Multi-level administration**: System Admin → State → District → Block → School
- **Student assessment**: Tests, marks entry, performance analytics
- **AI-powered tools**: Practice question generation, chatbot
- **District-scoped data isolation**: Each district's tests and student data are independent
- **Activity logging**: Full audit trail for district-level operations
- **Security**: Account lockout, session control, password expiry

### Data Hierarchy

```
System Admin
    └── State (e.g., Rajasthan)
            └── District (e.g., Jaipur) ← Collector Dashboard
                    └── Block (e.g., Sanganer)
                            └── School (e.g., Govt. Senior Secondary School)
                                    └── Student
```

---

## 2. Technology Stack & Prerequisites

| Component | Requirement |
|-----------|-------------|
| Python | 3.10 or higher |
| Django | 5.0 |
| Database | PostgreSQL 14+ (recommended) or SQLite (dev only) |
| Web Server | Gunicorn + Nginx (production) |
| OS | Ubuntu 22.04 LTS (recommended) / Windows 10+ (dev) |

### Required Python packages
Install from requirements:
```bash
pip install -r requirements.txt
```

Key packages used:
- `django-environ` — environment variable management
- `django-crispy-forms` + `crispy-bootstrap4` — form rendering
- `django-dbbackup` — database backup
- `whitenoise` — static file serving
- `django-simple-captcha` — CAPTCHA on login
- `openpyxl` — Excel file upload for students
- `openai`, `google-generativeai`, `sarvam` — AI features

---

## 3. Installation

### Step 1 — Clone / Copy the project
```bash
git clone <repository-url>
cd school_project
```

### Step 2 — Create and activate virtual environment
```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

---

## 4. Environment Configuration

The project uses **two `.env` files**:

### File 1: `school_project/.env`  (database + local overrides)

```env
# Database connection
DATABASE_URL=postgresql://YOUR_DB_USER:YOUR_DB_PASSWORD@localhost:5432/YOUR_DB_NAME

# Django debug mode (set False in production)
DEBUG=False

# Allowed hosts — add your server IP or domain
ALLOWED_HOSTS=your-server-ip,yourdomain.com,localhost,127.0.0.1

# Dropbox backup token (get from Dropbox App Console)
DROPBOX_ACCESS_TOKEN=your_dropbox_token_here

# Cookie security (True in production with HTTPS, False for HTTP dev)
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### File 2: `school_project/school_app/.env`  (API keys + secret)

```env
# Django secret key — generate a new unique key for each deployment
SECRET_KEY=your-unique-secret-key-min-50-chars

# AI service keys
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_gemini_key
SARVAM_API_KEY=your_sarvam_key
YOUTUBE_API_KEY=your_youtube_api_key
```

> **IMPORTANT:** Never commit `.env` files to version control. Each district/state deployment must have its own unique `SECRET_KEY`.

### Generate a new SECRET_KEY
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 5. Database Setup

### Step 1 — Create PostgreSQL database
```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE padhaiwithai_districtname;
CREATE USER your_db_user WITH PASSWORD 'your_db_password';
GRANT ALL PRIVILEGES ON DATABASE padhaiwithai_districtname TO your_db_user;
```

### Step 2 — Update DATABASE_URL in `.env`
```env
DATABASE_URL=postgresql://your_db_user:your_db_password@localhost:5432/padhaiwithai_districtname
```

### Step 3 — Run migrations
```bash
cd school_project
python manage.py migrate
```

This applies all 18 migrations in order and creates all tables.

### Step 4 — Collect static files
```bash
python manage.py collectstatic --noinput
```

---

## 6. First-Time Setup: Create Hierarchy

After migrations, set up the data hierarchy in this exact order:

### Step 1 — Create System Admin
```bash
python manage.py makesuperuser
```
Or via Django admin:
```bash
python manage.py createsuperuser
```
Log in at `/admin/` and set `is_system_admin = True` on the user.

### Step 2 — Create State
Log in as System Admin → **Manage → Create State**
URL: `/manage/states/create/`

Fields:
- State name (English)
- State name (Hindi/local language)
- Admin username & password (creates a new `is_state_user` account)

### Step 3 — Create District
Log in as **State Admin** → **Manage → Create District**
URL: `/manage/districts/create/`

Fields:
- District name (English + Hindi)
- Admin username & password (creates a new `is_district_user` / Collector account)

> One district = one Collector Dashboard. Repeat for each district in the state.

### Step 4 — Create Blocks
Log in as **District Admin** → **Manage → Create Block**
URL: `/manage/blocks/create/`

Fields:
- Block name (English + Hindi)
- Admin username & password (creates a new `is_block_user` account)

### Step 5 — Create Schools
Log in as **District Admin** or **Block Admin** → **Manage → Create School**
URL: `/manage/schools/create/`

Fields:
- School name
- DISE code (unique identifier)
- Block (select from dropdown)
- Admin username & password (creates a new `is_school_user` account)

---

## 7. User Roles Reference

| Role | Login URL | Flag | Can Do |
|------|-----------|------|--------|
| System Admin | `/login/` | `is_system_admin` | Create states, view all data, Django admin |
| State User | `/login/` | `is_state_user` | Create districts, view state dashboard, switch districts in Collector view |
| District User (Collector) | `/login/` | `is_district_user` | Create blocks/schools, add tests, view collector dashboard, activity logs |
| Block User | `/login/` | `is_block_user` | View block data, add marks |
| School User | `/login/` | `is_school_user` | Upload students, add/view marks |
| Student | `/student-login/` | session-based | View tests, take practice tests, view own marks |

### Password Policy (applies to all admin roles)
- Minimum 8 characters
- Expires every **90 days** (configurable: `PASSWORD_EXPIRY_DAYS` in settings)
- Account locked after **5 failed attempts** for **30 minutes** (configurable: `ACCOUNT_LOCKOUT_ATTEMPTS`, `ACCOUNT_LOCKOUT_DURATION`)

---

## 8. Student Data Upload

Students are loaded in bulk via Excel file.

### Upload URL
`/upload-student-data/`  (School User or District User)

### Excel Format
The Excel file must have these columns (header row required):

| Column | Description | Example |
|--------|-------------|---------|
| `name` | Student full name | Ramesh Kumar |
| `father_name` | Father's name | Suresh Kumar |
| `dob` | Date of birth (DD/MM/YYYY) | 15/08/2010 |
| `gender` | M / F | M |
| `school_code` | School DISE code | 080101001 |
| `class` | Class number | 10 |
| `section` | Section letter | A |
| `mobile` | Contact number | 9876543210 |

### After Upload
Run the password hashing command to hash plain-text passwords for new students:
```bash
python manage.py hash_student_passwords
```

> Run this after every bulk upload. Existing hashed passwords are not affected.

---

## 9. Test Management

Tests are **district-scoped** — each test belongs to one district and is only visible to students in that district.

### Create a Test
District Admin → **Add Test**
URL: `/add-test/`

Fields:
- Test name
- Subject name
- Test date
- Maximum marks
- Question paper PDF (optional)
- Answer key PDF (optional)

> When a District Admin creates a test, `district` is automatically set to their district. Students from other districts will not see this test.

### Activate / Deactivate Tests
From the Collector Dashboard test list, use the Activate/Deactivate buttons.
Only **active** tests are visible to students.

### Enter Marks
School User → **Add Marks**
URL: `/add-marks/`

Select test → select student → enter marks.

Or use bulk marks upload from the marks list page.

---

## 10. Collector (District) Dashboard

URL: `/collector-dashboard/`
Access: District Admin, State Admin (with district selector), System Admin

### Dashboard Sections

| Section | Description |
|---------|-------------|
| **Summary Cards** | Total schools, total tests, total students, active sessions |
| **Test Performance Table** | Avg marks, % score per test with student mark distribution by category |
| **School-wise Analysis** | School-level performance breakdown via raw SQL aggregation |
| **Category Chart** | Pie chart showing % of students in score bands (0-33, 33-60, 60-80, 80-90, 90-100, 100) |
| **Previous Year Data** | Historical data from `student_exam_results` table (if populated) |

### Test Count Logic
`Total Tests` = tests where `district = this district` (new tests) + tests where `district IS NULL` AND marks exist from this district's students (legacy backward-compatible tests).

### State Admin Multi-District View
State Admin can use the district dropdown at the top of the Collector Dashboard to switch between districts without logging out.

---

## 11. Security & Session Settings

All configurable in `settings.py` or via `.env`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `SESSION_COOKIE_AGE` | 1800 (30 min) | Auto logout after inactivity |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | True | Session ends on browser close |
| `ACCOUNT_LOCKOUT_ATTEMPTS` | 5 | Failed logins before lockout |
| `ACCOUNT_LOCKOUT_DURATION` | 30 (minutes) | Duration of lockout |
| `PASSWORD_EXPIRY_DAYS` | 90 | Force password change interval |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | 5 MB | Max upload file size |
| `X_FRAME_OPTIONS` | DENY | Clickjacking protection |
| `SECURE_CONTENT_TYPE_NOSNIFF` | True | MIME sniff protection |

### Force Password Change
If a user must reset their password immediately:
1. Django admin → CustomUser → check `must_change_password = True`
2. User will be redirected to change-password page on next login

---

## 12. Backup Configuration

The project uses **django-dbbackup** with **Dropbox** storage.

### Setup Dropbox
1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Create a new App → Scoped Access → Full Dropbox
3. Generate an access token
4. Add to `school_project/.env`:
   ```env
   DROPBOX_ACCESS_TOKEN=your_token_here
   ```

### Run Manual Backup
```bash
python manage.py dbbackup
```

### Schedule Automatic Backup (Linux cron)
```bash
# Edit crontab
crontab -e

# Add: backup every day at 2 AM
0 2 * * * /path/to/venv/bin/python /path/to/school_project/manage.py dbbackup >> /var/log/padhaiwithai_backup.log 2>&1
```

### Restore from Backup
```bash
python manage.py dbrestore
```
After restore, run:
```bash
python manage.py fix_after_restore
```

### Backup Retention
`DBBACKUP_CLEANUP_KEEP = 10` — keeps last 10 backups, older ones are deleted automatically.

---

## 13. Production Deployment Checklist

Work through this list before going live:

**Environment**
- [ ] `DEBUG=False` in `.env`
- [ ] `SECRET_KEY` is unique and at least 50 characters (never reuse from dev)
- [ ] `ALLOWED_HOSTS` includes only your domain/IP
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`

**Database**
- [ ] PostgreSQL (not SQLite) in production
- [ ] `python manage.py migrate` run successfully
- [ ] DB user has only necessary privileges (not superuser)

**Static & Media Files**
- [ ] `python manage.py collectstatic --noinput` run
- [ ] Nginx configured to serve `/static/` and `/media/` directories
- [ ] `MEDIA_ROOT` path has write permission for the app process

**Users & Data**
- [ ] System Admin created via `makesuperuser`
- [ ] State → Districts → Blocks → Schools hierarchy created
- [ ] Student data uploaded and `hash_student_passwords` run
- [ ] Default admin passwords changed

**Security**
- [ ] HTTPS certificate installed (Let's Encrypt recommended)
- [ ] Nginx configured with SSL redirect
- [ ] Firewall: only ports 80, 443, 22 open
- [ ] `.env` files not readable by web server (chmod 600)

**Backup**
- [ ] Dropbox token configured and tested (`python manage.py dbbackup`)
- [ ] Cron job scheduled for daily backup

**Monitoring**
- [ ] `LOGGING` pointed to file (not just console) in production
- [ ] Activity logs working: `/activity-logs/` accessible to district admin

---

## 14. Troubleshooting

### Problem: Migrations fail with interactive prompt about `max_marks`
**Cause:** Model drift between `max_marks` field and migration history.
**Fix:** Do NOT run `makemigrations` directly. All new migrations for this project are hand-written to avoid the drift prompt. Contact the developer to hand-write the next migration.

### Problem: Students cannot log in
**Steps:**
1. Check if account is locked: Django admin → Student → `locked_until` field
2. Check if password is hashed: run `python manage.py hash_student_passwords`
3. Verify student's school is active

### Problem: Collector dashboard shows 0 tests
**Cause:** Tests were created before district-scoping migration (0018), so `district = NULL`.
**Fix:** Old tests remain visible if they have marks from district students. To fully scope old tests, update them via Django shell:
```python
python manage.py shell
from school_app.models import Test, District
d = District.objects.get(name_english='YourDistrictName')
Test.objects.filter(district__isnull=True).update(district=d)
```

### Problem: Static files not loading in production
```bash
python manage.py collectstatic --noinput
# Then restart gunicorn
sudo systemctl restart gunicorn
```

### Problem: Session expires too quickly
Update in `settings.py`:
```python
SESSION_COOKIE_AGE = 60 * 60  # 1 hour
```

### Problem: Dropbox backup token expired
Dropbox short-lived tokens expire. Generate a long-lived token or set up OAuth2 refresh token via the Dropbox App Console.

### Problem: `DisallowedHost` error on new server
Add the server IP/domain to `ALLOWED_HOSTS` in `.env`:
```env
ALLOWED_HOSTS=192.168.1.100,newdomain.gov.in,localhost
```

---

## Appendix: Quick URL Reference

| URL | Who Can Access | Purpose |
|-----|---------------|---------|
| `/login/` | All admin roles | Admin login |
| `/student-login/` | Students | Student login |
| `/admin/` | System Admin | Django admin panel |
| `/collector-dashboard/` | District, State, System Admin | Main analytics dashboard |
| `/state-dashboard/` | State Admin | State overview |
| `/manage/states/` | System Admin | List/manage states |
| `/manage/districts/` | State Admin | List/manage districts |
| `/manage/blocks/` | District Admin | List/manage blocks |
| `/manage/schools/` | District/Block Admin | List/manage schools |
| `/add-test/` | District Admin | Create new test |
| `/upload-student-data/` | School/District Admin | Bulk student upload |
| `/activity-logs/` | District Admin | Audit trail |
| `/change-password/` | All admin users | Password change |

---

*Document prepared for PadhaiWithAI deployment — March 2026*
