# PadhaiWithAI — Complete Implementation & User Manual

*Version 2.0 · Rewritten July 2026 · Covers deployment, admin, teacher, and student features.*

---

> **How to use this manual**
> - Sections **1–7** are for **system administrators / deployment engineers**.
> - Sections **8–17** are for **district / school administrators & teachers**.
> - Section **18** is a **quick-reference guide for students**.
> - Sections **19–22** are cross-cutting: security, backups, deployment checklist, troubleshooting.
>
> Screenshot placeholders look like `![Login page](docs/screenshots/login.png)` — replace with real screenshots after the first live deployment. Save all screenshots to `docs/screenshots/` in the repo root.
> ASCII wireframes are provided inline for major screens so the manual is useful even before screenshots exist.

---

## Table of Contents

**Part I — Deployment**
1. [System Overview](#1-system-overview)
2. [Technology Stack & Prerequisites](#2-technology-stack--prerequisites)
3. [Installation](#3-installation)
4. [Environment Configuration](#4-environment-configuration)
5. [Database Setup](#5-database-setup)
6. [First-Time Hierarchy Setup](#6-first-time-hierarchy-setup)
7. [User Roles Reference](#7-user-roles-reference)

**Part II — Administration & Teaching**
8. [Student Data Upload](#8-student-data-upload)
9. [Test & Marks Management](#9-test--marks-management)
10. [Collector (District) Dashboard](#10-collector-district-dashboard)
11. [AI Question Paper Generator](#11-ai-question-paper-generator)
12. [Assigned Papers & OMR Grading](#12-assigned-papers--omr-grading)
13. [Academic Calendar](#13-academic-calendar)
14. [Toppers of the Week](#14-toppers-of-the-week)
15. [AI Sathi — Content Administration](#15-ai-sathi--content-administration)
16. [Analytics, Reports & Activity Logs](#16-analytics-reports--activity-logs)
17. [Attendance Management](#17-attendance-management)
17A. [Math Tools (Teacher & Admin)](#17a-math-tools-teacher--admin)

**Part III — Student Experience**
18. [Student Portal Guide](#18-student-portal-guide)

**Part IV — Operations**
19. [Security & Session Settings](#19-security--session-settings)
20. [Backup Configuration](#20-backup-configuration)
21. [Production Deployment Checklist](#21-production-deployment-checklist)
22. [Troubleshooting](#22-troubleshooting)
23. [Appendix — URL Reference](#23-appendix--url-reference)

---

# Part I — Deployment

## 1. System Overview

**PadhaiWithAI** is a hierarchical school management, assessment and AI-assisted learning platform, purpose-built for state and district education departments (initially deployed for Rajasthan / Tonk district). It combines a traditional school-ERP with modern AI features:

### Core capabilities

- 🏛 **5-level administration** — System → State → District → Block → School → Student
- 📊 **Assessment engine** — Tests, marks, attendance, performance analytics
- 🤖 **AI Sathi chatbot** — Chapter-aware AI tutor in Hindi and English (Sarvam AI)
- 🧮 **Math tools** — AI-powered problem solver + question generator (OpenAI + Sarvam)
- 📄 **AI question paper generator** — District-wide paper creation with PDF export
- 📱 **OMR grading** — Upload scanned answer sheets, auto-detect answers via OpenCV
- 📚 **Assigned papers** — Teachers assign, students take online
- 📅 **Academic calendar** — District-wide event scheduling
- 🏆 **Toppers showcase** — Weekly student recognition on public login page
- 🔍 **Analytics dashboards** — Multiple lenses at every hierarchy level
- 🛡 **Enterprise security** — Session isolation, IP rate-limiting, account lockout, audit logs

### Data hierarchy

```
System Admin
    └── State                       (e.g., Rajasthan)
            └── District            (e.g., Tonk) ← Collector Dashboard
                    └── Block       (e.g., Sanganer)
                            └── School  (e.g., Govt. Sr. Sec. School Dhundhiya)
                                    └── Student
```

Every data query is scoped by role — a School Admin sees only their school, a Block Admin sees only their block, etc. Cross-boundary access is only granted to Collectors, State users, and System Admins.

### Screenshot placeholder

![System hierarchy overview](docs/screenshots/01_hierarchy_overview.png)

---

## 2. Technology Stack & Prerequisites

| Component | Requirement | Notes |
|---|---|---|
| Python | 3.10+ (3.13 tested) | 3.12+ recommended |
| Django | 5.0.x | (Upgrade path to 5.2 LTS available) |
| Database | PostgreSQL 14+ | SQLite for dev only |
| Web server (Windows) | IIS + wfastcgi | Primary production target |
| Web server (Linux) | Gunicorn + Nginx | Alternative deployment |
| Static files | WhiteNoise | Serves via Django |
| Media storage | Local disk or Dropbox | Object storage optional |
| OS (server) | Windows Server 2019+ / Ubuntu 22.04 LTS | |
| OS (dev) | Windows 10+ / macOS / Linux | |

### External services required

| Service | Purpose | Free tier? |
|---|---|---|
| **Sarvam AI** | AI Sathi chat, question paper generation (Hindi-capable) | Paid |
| **OpenAI** | Math solver, image OCR | Paid |
| **Google Gemini** | Alternative AI provider | Free tier |
| **YouTube Data API** | Video suggestions for students | Free tier |
| **Dropbox** | Automated DB backups | Free tier (2GB) |

Get API keys from each provider's developer console and add to `.env` (see Section 4).

### Key Python packages

Full list in `requirements.txt`. Notable ones:

```
Django==5.0
psycopg2-binary
django-environ
django-crispy-forms + crispy-bootstrap4
django-dbbackup + dropbox
whitenoise
django-simple-captcha
openpyxl              # Excel uploads
Pillow                # Image processing
opencv-python         # OMR sheet detection
sarvamai              # Sarvam AI SDK
openai                # OpenAI SDK
google-generativeai   # Gemini SDK
wfastcgi              # Windows IIS support
```

Install:
```bash
pip install -r requirements.txt
```

---

## 3. Installation

### Step 1 — Get the code
```bash
git clone <repository-url>
cd PadhaiWithAIWithclaude03022026
```

### Step 2 — Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Verify Django can boot
```bash
cd school_project
python manage.py check
```

Should print `System check identified no issues (0 silenced).`

---

## 4. Environment Configuration

The project loads two `.env` files:

- `school_project/.env` — Deployment-specific (database, hosts, cookies)
- `school_project/school_app/.env` — Defaults (SECRET_KEY, API keys)

Priority: `school_project/.env` **overrides** `school_app/.env`.

### File 1: `school_project/.env`

```env
# ── Database ────────────────────────────────────────────────
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/DB_NAME

# ── Django core ─────────────────────────────────────────────
DEBUG=False
ALLOWED_HOSTS=your-domain.gov.in,10.1.2.3,localhost,127.0.0.1
SECRET_KEY=<generate-a-fresh-50-char-key-see-below>

# ── Cookie / session security ───────────────────────────────
SESSION_COOKIE_SECURE=True     # requires HTTPS
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True       # optional but recommended

# ── Media serving ───────────────────────────────────────────
SERVE_MEDIA_LOCALLY=True       # False if IIS/nginx serves /media/ directly

# ── Backup storage ──────────────────────────────────────────
DROPBOX_ACCESS_TOKEN=<your-dropbox-app-token>

# ── AI cost controls (optional) ─────────────────────────────
SARVAM_MODEL=sarvam-105b
SARVAM_MAX_TOKENS=4000
AI_SATHI_MSG_LIMIT=20
AI_SATHI_SESSION_MINS=30
```

### File 2: `school_project/school_app/.env`

```env
# ── AI provider keys ────────────────────────────────────────
SARVAM_API_KEY=<sarvam-api-key>
OPENAI_API_KEY=<openai-api-key>
GOOGLE_API_KEY=<gemini-api-key>
YOUTUBE_API_KEY=<youtube-data-v3-key>
```

### Generate a fresh SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> ⚠ **Never** reuse a SECRET_KEY across environments. If the same key is used in dev and prod, session cookies from dev can be forged for prod.

### Screenshot placeholder

![Env files layout](docs/screenshots/04_env_files.png)

---

## 5. Database Setup

### Step 1 — Create PostgreSQL database

```sql
CREATE DATABASE padhaiwithai_tonk;
CREATE USER padhai_user WITH PASSWORD 'strong_random_password';
GRANT ALL PRIVILEGES ON DATABASE padhaiwithai_tonk TO padhai_user;
```

### Step 2 — Update `DATABASE_URL` in `.env`

```env
DATABASE_URL=postgresql://padhai_user:strong_random_password@localhost:5432/padhaiwithai_tonk
```

### Step 3 — Run migrations

```bash
cd school_project
python manage.py migrate
```

**Current migration count: 30+** (as of this version). All migrations are hand-written where needed to avoid interactive prompts.

If migrating an **existing production DB** where table already exists (e.g. `school_app_topper`):

```bash
python manage.py migrate school_app <migration_number> --fake
```

### Step 4 — Collect static files

```bash
python manage.py collectstatic --noinput
```

Deploy the `staticfiles/` directory via IIS or Nginx.

### Screenshot placeholder

![Successful migration output](docs/screenshots/05_migrations_success.png)

---

## 6. First-Time Hierarchy Setup

Perform these steps **in order** — each level's admin can only create the next level.

### Step 1 — Create System Admin

```bash
python manage.py makesuperuser
```

This idempotent command creates a superuser with `is_system_admin = True`.

Or manually:
```bash
python manage.py createsuperuser
# Then log in to /admin/ and check `is_system_admin`
```

### Step 2 — Create State

Log in as **System Admin** → go to `/manage/states/`.

```
┌──────────────────────────────────────────────────┐
│  Manage States                    [+ Add State]  │
├──────────────────────────────────────────────────┤
│  Name (Eng)   Name (Hindi)   Admin      Actions  │
│  Rajasthan    राजस्थान        state@…    Edit    │
└──────────────────────────────────────────────────┘
```

Fields for a new state:
- State name (English + Hindi)
- Admin email + password → creates `is_state_user` account

### Step 3 — Create District

Log in as **State Admin** → `/manage/districts/`.

Fields:
- District name (English + Hindi)
- NIC code (optional)
- Admin email + password → creates `is_district_user` (Collector) account

> **One district = one Collector Dashboard.** Repeat for every district.

### Step 4 — Create Blocks

Log in as **District Admin** → `/manage/blocks/`.

Fields:
- Block name (English + Hindi)
- Admin email + password → creates `is_block_user` account

### Step 5 — Create Schools

Log in as **District** or **Block Admin** → `/manage/schools/`.

Fields:
- School name
- **NIC code / DISE code** (unique identifier)
- Block (dropdown)
- Admin email + password → creates `is_school_user` account

### Screenshot placeholders

- ![Manage states page](docs/screenshots/06a_manage_states.png)
- ![Create district form](docs/screenshots/06b_create_district.png)
- ![Manage schools with NIC code](docs/screenshots/06c_manage_schools.png)

---

## 7. User Roles Reference

| Role | Login URL | Flag | Primary capabilities |
|---|---|---|---|
| System Admin | `/login/` | `is_system_admin` | All actions, Django admin, all districts |
| State User | `/login/` | `is_state_user` | Manage districts, view all districts in state |
| District User (Collector) | `/login/` | `is_district_user` | Collector Dashboard, manage blocks/schools/tests, toppers, calendar |
| Block User | `/login/` | `is_block_user` | View block-level data, mark attendance |
| School User (Teacher) | `/login/` | `is_school_user` | Upload students, enter marks, assign papers, **use Math Tools + AI Sathi + Question Paper Generator** |
| Student | `/student-login/` | session-based | Take practice tests, chat with AI Sathi, view marks |

### Password policy (all admin roles)

- Minimum 8 characters
- Expires every **90 days** (setting: `PASSWORD_EXPIRY_DAYS`)
- Account locked after **5 failed attempts** for **30 minutes**
- **IP-level rate limit**: 20 failed attempts per IP → 30-min block
- Force-change flag: set `must_change_password = True` in Django admin for any user

### Session policy

- 30-minute inactivity timeout
- **Single-session enforcement**: New login invalidates the previous session
- Logout kills all tracked sessions for that user
- Session security uses `current_session_key` field on both `CustomUser` and `Student`

### Screenshot placeholder

![Login page with captcha](docs/screenshots/07_login_page.png)

---

# Part II — Administration & Teaching

## 8. Student Data Upload

Students are bulk-loaded via Excel.

### Upload URL

`/upload-student-data/` — School User or District Admin

### Excel format (required columns in header row)

| Column | Required | Type | Example |
|---|---|---|---|
| `name` | ✅ | Text | Ramesh Kumar |
| `father_name` |  | Text | Suresh Kumar |
| `dob` |  | Date (DD/MM/YYYY) | 15/08/2010 |
| `gender` |  | M / F / O | M |
| `school_code` | ✅ | Text (must match school NIC) | 080101001 |
| `class_name` | ✅ | Text | 10 |
| `section` |  | Text | A |
| `mobile` |  | Text | 9876543210 |
| `roll_number` | ✅ (unique per school) | Text | 202510012345 |

Download sample from `/download-sample-student-excel/`.

### Security features on upload

Every uploaded file goes through:
1. **Extension check** (`.xlsx` or `.xls` only)
2. **Size limit** (5 MB max)
3. **Magic-byte validation** — actual file content matches declared type
4. **Formula injection sanitization** — cells starting with `=`, `+`, `-`, `@` get a leading `'`

### After upload

The system automatically:
- Sets **default password to `1234`** for new students
- Sets **`must_change_password = True`** — student is forced to change on first login
- Sends student to `/student-change-password/` immediately after their first successful login

> ⚠ **Legacy passwords**: If plain-text passwords exist from before hashing was enforced, run `python manage.py hash_student_passwords`. Existing hashed passwords are not re-hashed.

### Screenshot placeholders

- ![Excel upload form](docs/screenshots/08a_upload_students.png)
- ![Sample Excel format](docs/screenshots/08b_sample_excel.png)

---

## 9. Test & Marks Management

Tests are **district-scoped** — each test belongs to exactly one district. Students from other districts cannot see or attempt them.

### Create a test

District Admin → `/add-test/`

Fields:
- Test name
- Subject
- Test date
- Maximum marks
- Question paper PDF (optional)
- Answer key PDF (optional)

When a district admin creates a test, `district` auto-populates from their profile.

### Activate / deactivate

Only **active** tests appear on students' dashboards. Toggle from `/collector-dashboard/` test list.

**Security note (V-C4):** Test activation/deactivation redirects to the `Referer` header, but the URL is validated against `ALLOWED_HOSTS` — open-redirect attacks are blocked.

### Enter marks

**Individual entry**: School User → `/marks/add/` → select test, student, enter mark.

**Bulk entry**: `/test-marks-entry/<test_id>/` — grid view for entire class.

Or use the automated grading paths:
- **AI paper**: See Section 11
- **OMR**: See Section 12

### Marks table sortable columns

The `/view-test-results/<test_number>/` page allows sorting by:
- Student name (default)
- Roll number
- Class name
- Marks (ascending/descending)

*Sort field is whitelisted server-side to prevent ORM sort injection (V-C2 fix).*

### Screenshot placeholder

![Add test form](docs/screenshots/09a_add_test.png)
![Marks entry grid](docs/screenshots/09b_marks_entry.png)

---

## 10. Collector (District) Dashboard

URL: `/collector-dashboard/`
Access: District Admin (own district), State Admin (any district in state), System Admin (any)

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Collector Dashboard — Tonk District       [Logout]       │
├──────────────────────────────────────────────────────────────┤
│  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐                    │
│  │Schools│ │Tests  │ │Students│ │Active │                    │
│  │  247  │ │  32   │ │ 11,847│ │Sessions│                   │
│  └───────┘ └───────┘ └───────┘ └───────┘                    │
│                                                              │
│  ┌── Category Distribution ──┐ ┌── Test Performance ────┐   │
│  │      [Pie chart]           │ │  Test Name | Avg %    │   │
│  │  ● 0-33%   12%             │ │  Unit-1    | 62.3%    │   │
│  │  ● 33-60%  38%             │ │  Unit-2    | 58.7%    │   │
│  │  ● 60-80%  30%             │ │  ...                  │   │
│  │  ● 80-90%  15%             │ └───────────────────────┘   │
│  │  ● 90-100%  5%             │                              │
│  └────────────────────────────┘                              │
│                                                              │
│  📋 Quick Actions                                            │
│  [Upload Students] [Add Test] [Reports] [Manage Toppers]     │
│  [Academic Calendar] [Activity Logs] [Change Password]       │
└──────────────────────────────────────────────────────────────┘
```

### Sections

| Section | What it shows |
|---|---|
| Summary cards | Total schools, tests, students, live sessions |
| Test performance table | Avg %, category distribution per test |
| School-wise analysis | Avg performance per school (via aggregated SQL) |
| Category chart | % of students in score bands (0-33, 33-60, 60-80, 80-90, 90-100) |
| Previous year data | Historical `student_exam_results` view (if populated) |

### State admin district switcher

State admins see a **district dropdown** at the top of the Collector Dashboard — pick any district to view its data without logging out.

### Quick actions row

Buttons on the dashboard link to key admin flows:
- Upload students
- Add test
- Report dashboard
- **Manage Toppers** (see Section 14)
- Academic calendar
- Activity logs
- Change password

### Screenshot placeholder

![Collector Dashboard](docs/screenshots/10_collector_dashboard.png)

---

## 11. AI Question Paper Generator

Teachers and district admins can generate a complete question paper (with answers) using AI.

### URL

`/question-paper/`
Access: District Admin, School Admin

### Workflow

```
┌─────────────────────────────────────────────────────────┐
│  📄 AI Question Paper Generator                        │
├─────────────────────────────────────────────────────────┤
│  Class: [10 ▼]   Subject: [Maths ▼]  Language: [Hindi▼]│
│  Chapter: [Polynomials ▼]                              │
│  Difficulty: [Medium ▼]  Time: [90 min]                │
│  Sections: [A: MCQ x10] [B: 2-mark x5] [C: 5-mark x3]  │
│                                                         │
│  [🪄 Generate Question Paper]                          │
├─────────────────────────────────────────────────────────┤
│  ⚠ AI-generated content — verify before use.           │
│  ⚠ AI द्वारा तैयार सामग्री — उपयोग से पहले जांच करें।│
│                                                         │
│  Preview:                                              │
│  ┌─────────────────────────────────────────────────┐  │
│  │  GOVT. SR. SEC. SCHOOL DHUNDHIYA               │  │
│  │  Maths — Class 10 · Polynomials                │  │
│  │  Total Marks: 50 · Time: 90 min                │  │
│  │  Section A: MCQ (1 mark each)                  │  │
│  │  Q1. What is the degree of P(x) = 3x² + 2? [1] │  │
│  │  ...                                           │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  [⬇ Download PDF] [🖨 Print Paper] [🗝 Print Answers]  │
└─────────────────────────────────────────────────────────┘
```

### Steps

1. Select **Class, Subject, Chapter, Language, Difficulty, Total time**
2. Configure **Sections** (A/B/C/D) with marks-per-question and count
3. Click **Generate Question Paper** — takes 30–90 seconds depending on model
4. Review the preview — questions and answers appear side by side
5. Click **Download PDF** to save, or **Print Paper / Answer Key** to send to printer

### Features

- 📌 **Bilingual disclaimer** appears above every generated paper (English + Hindi)
- 📄 **Persistent footnote** on printed PDF — the disclaimer travels with the paper
- 💾 **History** — every generated paper saved to `/question-paper-history/`
- 🎯 **Assign** — teacher can immediately push the paper to students (see Section 12)
- 🔁 **Per-section retry** — if AI fails on one section, only that section regenerates

### AI provider notes

- Uses **Sarvam AI** with `SARVAM_MODEL` env var (default: `sarvam-105b`)
- Reasoning content fallback handled — no crashes on `NoneType` content
- **Prompt-injection guard**: session variables (`language`, `subject`, `chapter`) validated against whitelist before insertion into AI prompt

### Screenshot placeholders

- ![Question paper form](docs/screenshots/11a_qp_form.png)
- ![Generated paper preview](docs/screenshots/11b_qp_preview.png)
- ![History page](docs/screenshots/11c_qp_history.png)

---

## 12. Assigned Papers & OMR Grading

Once a paper is generated (Section 11), teachers can assign it to their class in two modes:

### Mode A — Online (students take it in the browser)

1. From `/question-paper-history/` click **Assign** on any paper
2. Choose class and duration (30 / 60 / 90 min)
3. Save — students see it under `/student-assigned-papers/` immediately
4. Students click **Take Paper** → timer starts → submit → auto-graded
5. Teacher views results at `/assignment-report/<paper_id>/`

### Mode B — Offline + OMR (printed papers, scanned answer sheets)

1. From paper history, click **Download OMR Sheets** (`/omr-sheets/`)
2. Print the OMR bubble sheets with QR codes for each student
3. Students fill bubbles physically → collect sheets
4. Teacher scans/photographs the sheets and uploads via `/omr-upload/`
5. **OpenCV pipeline** detects:
   - QR code → identifies the student
   - Filled bubbles → captures answers
6. Teacher reviews low-confidence detections at `/omr-confirm/`
7. Marks saved to the standard `Marks` table

### OMR pipeline internals

- **Image safety**: `open_image_safely()` prevents decompression bombs (V-V12)
- **20 MB max** upload
- **QR format**: `PAI:<student_id>:<paper_id>`
- **Confidence score**: 0.0–1.0 based on bubble contrast — below 0.75 flagged for manual review

### Screenshot placeholders

- ![Assign paper dialog](docs/screenshots/12a_assign_paper.png)
- ![OMR sheet layout](docs/screenshots/12b_omr_sheet.png)
- ![OMR review page](docs/screenshots/12c_omr_review.png)

---

## 13. Academic Calendar

District admins publish an academic calendar visible to all users in the district.

### Manage view

URL: `/academic-calendar/manage/`
Access: District Admin only

Events are shown in **descending date order** (newest first) with a calendar visualisation.

### Add event

Fields:
- **Title**
- **Event type**: Teaching / Exam / Holiday / Meeting / Other
- **Start date** and **End date**

Each event type is colour-coded:

| Type | Colour |
|---|---|
| Teaching | Blue #1e3c72 |
| Exam | Red #dc2626 |
| Holiday | Green #059669 |
| Meeting | Amber #d97706 |
| Other | Purple #6d28d9 |

### Public view

URL: `/academic-calendar/`
Access: Any logged-in user (block / school / teacher)

Read-only display with FullCalendar-style grid.

### Screenshot placeholders

- ![Calendar management view](docs/screenshots/13a_calendar_manage.png)
- ![Public calendar view](docs/screenshots/13b_calendar_public.png)

---

## 14. Toppers of the Week

Weekly student achievement showcase on the public login page.

### Manage view

URL: `/district/toppers/`
Access: **District Admin only**

Shows all toppers uploaded for schools in the district, with filter by status (Active / Hidden) and by school.

### Upload a topper

URL: `/district/toppers/upload/`

Fields:
- **Name** (required)
- **Caption** — optional, e.g. "Class 10 — 98% in Maths"
- **School** — dropdown restricted to schools in the district
- **Photo** (required) — JPEG/PNG/WEBP, max 2 MB
- **Week start** (auto-fills current Monday)
- **Week end** (auto-fills current Sunday)
- **Display order** — lower = higher priority
- **Active** checkbox

### Automatic image processing

Every uploaded photo is:
1. **Verified** against magic-byte check (rejects renamed files)
2. **EXIF-rotated** to correct orientation
3. **Centre-cropped** to square (biased 40% upward — keeps faces visible)
4. **Resized** to 400×400 pixels
5. **Re-encoded** as JPEG at quality 85
6. **EXIF-stripped** (privacy: removes GPS / device metadata)

Typical file-size reduction: 5 MB phone photo → ~30 KB JPEG.

### Login page display

Only toppers with:
- `is_active = True`
- `week_start ≤ today ≤ week_end`

...appear on the public login page in an auto-scrolling ticker.

### Actions

| Button | Effect |
|---|---|
| ✏ Edit | Update details or replace photo |
| 🙈 Hide / 👁 Show | Toggle `is_active` (no delete) |
| 🗑 Delete | Permanent removal + image file cleanup |

### Screenshot placeholders

- ![Topper list](docs/screenshots/14a_topper_list.png)
- ![Topper upload form](docs/screenshots/14b_topper_upload.png)
- ![Login page ticker](docs/screenshots/14c_login_toppers.png)

---

## 15. AI Sathi — Content Administration

The AI Sathi chatbot is chapter-aware: it knows what chapter the student is studying and tailors responses. This requires a curriculum tree to be set up first.

### Content model

```
AISathiClass (Class 6–12)
    └── AISathiSubject (Maths, Science, English, ...)
            └── AISathiChapter (Real Numbers, Polynomials, ...)
                    ├── description
                    └── starter_questions (JSON list)
```

### Management URL

`/manage-classes/`, `/manage-subjects/`, `/manage-chapters/`
Access: State admin

### Add a chapter

- Class (dropdown from `AISathiClass`)
- Subject (dropdown from `AISathiSubject` filtered by class)
- Chapter name (English)
- Description (optional, feeds into the AI system prompt)
- Starter questions (JSON list of 5–12 sample questions)
- Order (display sort)
- Active checkbox

### Starter questions example

```json
[
  "What is this chapter about?",
  "Give me key formulas and definitions",
  "Explain with a real-life example",
  "What are common exam questions?",
  "Quiz me on this chapter",
  "Solve a practice problem step by step"
]
```

If left empty, the system supplies **language-appropriate defaults** — English or Hindi based on the student's selection.

### Screenshot placeholder

![Chapter management](docs/screenshots/15_manage_chapters.png)

---

## 16. Analytics, Reports & Activity Logs

Multiple analytics dashboards at different hierarchy levels.

### Analysis Dashboard

URL: `/analysis-dashboard/`
Access: Any admin with hierarchy access

Layout (top to bottom):
1. **Student Information** — name, roll, class, school
2. **Test Performance Details** — every test with marks, %, and grade
3. **Performance Statistics** — bar chart of subject-wise average

The API `/get-student-analysis/<student_id>/` is **hierarchy-scoped** (V-C1 fix) — admins can only view students under their scope, never students in other districts.

### Report Dashboard

URL: `/report-dashboard/`
Access: District Admin

Aggregated reports:
- Schools with / without students
- Schools with / without tests
- Schools with average marks
- Test-wise averages
- Top students, weakest students
- Historical analysis

### Activity Logs

URL: `/activity-logs/`
Access: District Admin

Full audit trail of every action:
- User logins (success and failure with IP)
- Password changes
- Test creation / activation
- Topper upload / edit / delete
- Marks entry
- OMR grading
- Assignment creation

Filterable by user, action type, date range.

### Screenshot placeholders

- ![Analysis dashboard](docs/screenshots/16a_analysis.png)
- ![Activity logs](docs/screenshots/16b_activity_logs.png)

---

## 17. Attendance Management

### Daily attendance entry

School User → `/submit-attendance/`

Grid view: All students of a class × checkboxes for present.

### Reports

| URL | Level |
|---|---|
| `/attendance-summary/` | School-level daily |
| `/school-daily-attendance-summary/` | School × date |
| `/block-wise-attendance-summary/` | Block roll-up |
| `/district-wise-attendance-summary/` | District roll-up |
| `/date-wise-attendance-summary/` | Cross-district by date |
| `/block-attendance-report/` | Block admin's local report |

### Screenshot placeholder

![Attendance entry](docs/screenshots/17_attendance.png)

---

## 17A. Math Tools (Teacher & Admin)

Math Tools is a shared AI-powered utility available to **both administrators (teachers) and students**. From the **School Admin dashboard**, look for the AI-tagged 🧮 **Solve Math** card.

### Access

| Role | Where to find it |
|---|---|
| System Admin | System Admin dashboard → "Solve Math" card |
| State Admin | State dashboard (deep link) |
| District Admin (Collector) | Collector dashboard (deep link) |
| Block Admin | Block dashboard (deep link) |
| **School Admin (Teacher)** | **School dashboard → "🧮 Solve Math" card** |
| Student | Student dashboard → "Math Tools" quick action |

**URL:** `/math-tools/`

### Two engines side by side

The School dashboard shows **two buttons** for Math Tools:

- **Math Tools (S)** → uses **Sarvam AI** — Hindi-friendly, tuned for Indian curriculum
- **Math Tools (C)** → uses **OpenAI GPT (ChatGPT-style)** — English-first, strong for algebra/calculus

Teachers can switch engines to compare answers for a difficult problem, or pick the one their students respond to better.

### Workflow

```
┌──────────────────────────────────────────────────────────────┐
│  🧮 Math Tools — AI Powered Solutions          Model: SARVAM │
├──────────────────────────────────────────────────────────────┤
│  📚 Select Options            │   📝 Selected Questions      │
│  ├── Book:    [Class 10 ▼]   │   1. Solve xÂ² + 5x + 6 = 0   │
│  ├── Chapter: [Real Nos ▼]   │   2. Find HCF of 24 and 36    │
│  └── Load Questions          │                               │
│                              │   [Solve All] [Generate More] │
│                              │   [Clear]                     │
├──────────────────────────────────────────────────────────────┤
│  ⚠ AI-generated content. Cross-check calculations before use.│
│  ⚠ AI द्वारा तैयार सामग्री। परीक्षा में उपयोग से पहले जांचें।│
│                                                              │
│  ✨ AI Solutions                                             │
│  Q: Solve xÂ² + 5x + 6 = 0                                   │
│  Step 1: Factor → (x + 2)(x + 3) = 0                        │
│  Step 2: x = -2 or x = -3                                   │
│  Final Answer: x = -2, -3                                   │
│                                                              │
│  [🔄 Solve Again] [📄 Download PDF]                          │
└──────────────────────────────────────────────────────────────┘
```

### Two ways to use it

**Way 1 — Solve existing questions**
1. Pick book + chapter → click **Load Questions**
2. NCERT questions from that chapter appear
3. Select the ones you want solved
4. Click **Solve** → step-by-step solutions with LaTeX-formatted math

**Way 2 — Generate practice questions**
1. Pick book + chapter → click **Generate**
2. AI creates new practice questions in the style of the chapter
3. Use them for classroom practice or extra homework

### Features specific to Math Tools

| Feature | Detail |
|---|---|
| **LaTeX-rendered math** | Fractions, exponents, roots display properly via MathJax |
| **Step-by-step solutions** | Each problem shows working, not just the answer |
| **"Solve Again" button** | AI rewrites the solution in simpler language for weaker students |
| **PDF download** | Each solution card has its own PDF export button |
| **AI disclaimer** | Yellow banner + PDF embedded footer (see Section 15's disclaimer rules) |
| **Image input** | Upload a photo of a handwritten problem (via `/ask-pai/`) |

### PDF export

Each solution card has a **📄 Download PDF** button. The generated PDF:
- Includes the PadhaiWithAI watermark
- Embeds the **AI disclaimer** at the top (in English + Hindi)
- Auto-scales to fit A4
- Preserves LaTeX rendering as pixels

Teachers use this to hand out solution sets after class.

### Ask PAI (bonus)

URL: `/ask-pai/`
A simplified single-question interface. Type any math question in Hindi or English → get an answer. Also supports uploading a photo of a written question.

### Screenshot placeholders

- ![Math Tools main page](docs/screenshots/17A_math_tools.png)
- ![Solutions display with LaTeX](docs/screenshots/17A_math_solutions.png)
- ![Ask PAI interface](docs/screenshots/17A_ask_pai.png)

### Content bank

Math Tools reads chapters from `school_app/content/`. Currently:
- `english_class_10/` — 14 chapters
- `hindi_class_10/` — 14 chapters

To add more classes / subjects, follow the JSON schema in `content.json`:
```json
{
  "book_name": "Mathematics - Class 10",
  "language": "English",
  "class": "10",
  "chapters": [
    {"id": 1, "name": "Real Numbers"},
    {"id": 2, "name": "Polynomials"}
  ]
}
```

Each chapter has its own `chapter<N>.json` with question data. **Path traversal is prevented** — book IDs must match `^[A-Za-z0-9_\-]+$`.

---

# Part III — Student Experience

## 18. Student Portal Guide

### Login

URL: `/student-login/`

Students log in with **roll number + password** (not email).

- Default password: `1234` on first-ever login → immediately forced to change
- 5 wrong attempts → account locked for 30 minutes
- 20 wrong attempts from one IP (any roll number) → IP blocked for 30 minutes
- Captcha (math question) on every login

### Student dashboard

URL: `/student-dashboard/`

```
┌────────────────────────────────────────────────────────────┐
│  Welcome, Ramesh Kumar (Class 10, Roll 202510012345)      │
├────────────────────────────────────────────────────────────┤
│  📊 Your Performance                                       │
│  Total tests: 12 · Avg: 68% · Highest: 88% · Lowest: 42%  │
│                                                            │
│  📅 Attendance: 87% (218/250 days)                        │
│                                                            │
│  🎯 Recent tests                                          │
│  1. Unit-3 Maths     72%     [View]                       │
│  2. Half-yearly Sci  81%     [View]                       │
│                                                            │
│  🚀 Quick actions                                         │
│  [🤖 AI Sathi] [🧮 Math Tools] [📝 Practice Tests]        │
│  [📚 Doubt Solver] [🎬 Video Learning]                    │
└────────────────────────────────────────────────────────────┘
```

### Features

| URL | Feature | Description |
|---|---|---|
| `/student-dashboard/` | Home | Performance summary + quick actions |
| `/ai_sathi/` | AI Sathi chat | Chapter-aware Hindi/English AI tutor |
| `/math-tools/` | Math solver | Enter a math problem, get step-by-step solution |
| `/student-practice-test/` | Practice test | AI-generated MCQs on selected chapter |
| `/student-recommendations/` | Recommendations | Video suggestions based on weak areas |
| `/student-doubt-solver/` | Doubt solver | Upload photo of a doubt, get AI answer |
| `/student-video-learning/` | Video learning | YouTube search integrated |
| `/student-tests/` | Test list | View available tests |
| `/student-performance/` | Performance | Detailed marks + graphs |
| `/student-assigned-papers/` | Assigned papers | Papers assigned by teachers |
| `/student-change-password/` | Password | Change with captcha (V-V25 fix) |

### AI Sathi flow

```
┌────────────────────────────────────────────────────────────┐
│  🤖 AI Sathi                            [🌙 Dark] [🔄 New]│
├────────────────────────────────────────────────────────────┤
│  Class: [10] Subject: [Maths] Chapter: [Real Numbers ▼]   │
│  Language: [Hindi ▼]                                      │
│  [Start Learning]                                         │
├────────────────────────────────────────────────────────────┤
│  💡 Suggested starters                                    │
│  [यह अध्याय किस बारे में है?] [मुख्य सूत्र बताइए]         │
│  [मुझे क्विज़ लीजिए] [परीक्षा में क्या आता है?]           │
├────────────────────────────────────────────────────────────┤
│  Type your question…       [📎] [🎙] [Send ▶]             │
└────────────────────────────────────────────────────────────┘
```

**Language-aware behavior:**
- Starter chips flip between Hindi and English instantly on dropdown change
- Typing suggestions match the selected language
- AI response is generated in the selected language
- Suggestions **only activate after** "Start Learning" is clicked

**Rate limits:**
- 30 messages per minute (rate-limited)
- 20 messages per session (default; env-configurable)
- 30-minute session lifespan

### AI disclaimers (mandatory reading)

Every AI-generated answer displays in a yellow warning banner:

> ⚠ **AI-generated content.** Cross-check calculations and methods before using in exams. AI can occasionally make mistakes.
> ⚠ **AI द्वारा तैयार सामग्री।** परीक्षा में उपयोग से पूर्व गणना की जांच अवश्य करें।

For downloaded PDFs (math solver, question paper), the disclaimer is **embedded** in the file so it travels with the artefact.

### Screenshot placeholders

- ![Student dashboard](docs/screenshots/18a_student_dashboard.png)
- ![AI Sathi chat](docs/screenshots/18b_ai_sathi.png)
- ![Math tools solver](docs/screenshots/18c_math_tools.png)
- ![Practice test](docs/screenshots/18d_practice_test.png)

---

# Part IV — Operations

## 19. Security & Session Settings

### Key settings (in `settings.py` or `.env`)

| Setting | Default | Purpose |
|---|---|---|
| `SESSION_COOKIE_AGE` | 1800 (30 min) | Auto-logout after inactivity |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | True | Session ends on browser close |
| `SESSION_COOKIE_SECURE` | env-based | HTTPS-only session cookie |
| `CSRF_COOKIE_SECURE` | env-based | HTTPS-only CSRF cookie |
| `SECURE_SSL_REDIRECT` | env-based | Force HTTPS redirect |
| `SECURE_HSTS_SECONDS` | 31536000 | 1-year HSTS |
| `ACCOUNT_LOCKOUT_ATTEMPTS` | 5 | Failed logins before account lock |
| `ACCOUNT_LOCKOUT_DURATION` | 30 min | Duration of account lock |
| `LOGIN_IP_MAX_FAILS` | 20 | IP-level rate-limit threshold |
| `LOGIN_IP_LOCK_MINS` | 30 min | IP-level block duration |
| `PASSWORD_EXPIRY_DAYS` | 90 | Force password change after |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | 5 MB | Max upload file size |

### Security controls implemented

| # | Feature | Where |
|---|---|---|
| ✅ | Captcha on admin login | `login_view` |
| ✅ | Captcha on student login | `student_login` |
| ✅ | Captcha on password change | `student_change_password` |
| ✅ | Per-account lockout | `student_login`, `login_view` |
| ✅ | Per-IP rate limit | `login_ip_blocked()` helper |
| ✅ | Session key rotation on login | `cycle_key()` |
| ✅ | Single-session enforcement | `current_session_key` field |
| ✅ | Logout invalidates all sessions | `logout_view`, `student_logout` |
| ✅ | Password expiry (90 days) | `SecurityMiddleware` |
| ✅ | Force password change flag | `must_change_password` |
| ✅ | ORM sort injection blocked | `view_test_results` whitelist |
| ✅ | Path traversal blocked | `_safe_book_dir()` |
| ✅ | Open redirect blocked | `_safe_referer()` |
| ✅ | Excel magic-byte validation | `validate_excel_upload()` |
| ✅ | Excel formula sanitization | `sanitize_cell()` |
| ✅ | Image bomb protection | `open_image_safely()` |
| ✅ | Error message sanitization | Generic responses, `logger.exception` |
| ✅ | CSP + X-Frame-Options + HSTS | `SecurityMiddleware` |

### Force password change for a user

Django admin → CustomUser (or Student) → set `must_change_password = True`.
User is redirected to change-password page on next login.

---

## 20. Backup Configuration

Backups use **django-dbbackup** with **Dropbox** storage.

### Dropbox setup

1. Go to https://www.dropbox.com/developers/apps
2. Create App → Scoped Access → Full Dropbox
3. Generate an access token (long-lived if possible)
4. Add to `.env`:
   ```
   DROPBOX_ACCESS_TOKEN=<token>
   ```

### Manual backup

```bash
python manage.py dbbackup
```

### Custom wrapper

```bash
python manage.py backup_db
```

This calls `dbbackup` then logs it in `ActivityLog` for audit trail.

### Scheduled backup (Linux cron)

```bash
crontab -e
# Add:
0 2 * * * /path/to/venv/bin/python /path/to/school_project/manage.py dbbackup >> /var/log/padhaiwithai_backup.log 2>&1
```

### Scheduled backup (Windows Task Scheduler)

Create a Basic Task:
- Trigger: Daily at 02:00
- Action: Start a program
- Program: `D:\path\to\venv\Scripts\python.exe`
- Arguments: `D:\path\to\school_project\manage.py dbbackup`

### Restore

```bash
python manage.py dbrestore
python manage.py fix_after_restore   # cleans up post-restore inconsistencies
```

### Retention

`DBBACKUP_CLEANUP_KEEP = 10` — last 10 backups kept, older auto-deleted.

---

## 21. Production Deployment Checklist

Work through this before going live:

### Environment
- [ ] `DEBUG=False` in `.env`
- [ ] `SECRET_KEY` freshly generated (50+ chars, no `django-insecure-` prefix)
- [ ] `ALLOWED_HOSTS` restricted to your domain / server IP
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] `SECURE_SSL_REDIRECT=True`
- [ ] `SERVE_MEDIA_LOCALLY` decided (True for simple, False if IIS/nginx serves)

### Dependencies
- [ ] `pip install -r requirements.txt` succeeds without errors
- [ ] `python manage.py check` passes
- [ ] Consider Django upgrade: 5.0 → 5.2 LTS for CVE coverage

### Database
- [ ] PostgreSQL 14+ (not SQLite)
- [ ] `python manage.py migrate` run successfully
- [ ] DB user has only necessary privileges (not `SUPERUSER`)
- [ ] Backup taken before first-time production data import

### Static & media
- [ ] `python manage.py collectstatic --noinput` run
- [ ] IIS / Nginx configured to serve `/static/` from `staticfiles/`
- [ ] IIS / Nginx configured to serve `/media/` from `media/`
- [ ] `MEDIA_ROOT` writable by app process
- [ ] `WhiteNoise` configured with `CompressedManifestStaticFilesStorage`

### Users & data
- [ ] System Admin created (`makesuperuser`)
- [ ] State → Districts → Blocks → Schools hierarchy created
- [ ] AI Sathi curriculum populated (classes/subjects/chapters)
- [ ] Student data uploaded
- [ ] Default admin passwords all changed
- [ ] Initial toppers uploaded (optional but improves login page)

### Security
- [ ] HTTPS certificate installed (Let's Encrypt or CA-issued)
- [ ] Firewall: only 80, 443, 22 open (RDP for Windows)
- [ ] `.env` files not readable by web server user (`chmod 600` on Linux)
- [ ] API keys rotated from dev values
- [ ] Provider spend caps set (Sarvam dashboard, OpenAI dashboard)

### Backup
- [ ] Dropbox token configured and tested (`python manage.py dbbackup`)
- [ ] Cron job / Task Scheduler configured for daily backup
- [ ] Backup restore tested at least once

### Monitoring
- [ ] Django logs pointed to file, not just console
- [ ] Activity logs accessible via `/activity-logs/`
- [ ] IIS / Nginx access logs enabled and rotated
- [ ] Watch for `SECURITY:` prefix in logs (indicates IDOR / rate-limit hits)

### Compliance & content
- [ ] Legal review of AI disclaimers (see manual Section 15)
- [ ] Privacy policy published at `/privacy-policy/`
- [ ] Terms of use published
- [ ] Grievance officer contact published

---

## 22. Troubleshooting

### 22.1 Migrations

**Problem:** `makemigrations` prompts for a nullable default interactively.
**Fix:** Do NOT run `makemigrations` automatically. Migrations for this project are hand-written where a prompt would appear (e.g., `0027_student_gender`, `0028_student_must_change_password`, `0029_student_current_session_key`, `0030_topper`). Contact the developer for the next migration.

**Problem:** Column already exists error on production DB.
**Fix:** The table already has the column. Run `python manage.py migrate school_app <migration_number> --fake` to register without executing.

### 22.2 Student login

**Problem:** Student can't log in with default password `1234`.
**Steps:**
1. Django admin → Student → check `locked_until` field
2. Verify `password` field starts with `pbkdf2_sha256$` (hashed) — if plain text, run `python manage.py hash_student_passwords`
3. Verify `is_active = True`
4. Verify `must_change_password` state — student may be stuck on change-password page

**Problem:** "Too many failed attempts from this network."
**Cause:** IP-level rate limit hit (20 failures in 10 min).
**Fix:** Wait 30 minutes, or clear cache:
```bash
python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

### 22.3 AI features

**Problem:** Sarvam AI returns "Model 'sarvam-m' has been deprecated."
**Fix:** `sarvam-m` is deprecated. Set `SARVAM_MODEL=sarvam-105b` in `.env`, restart server.

**Problem:** `'NoneType' object has no attribute 'strip'` on Sarvam response.
**Fix:** Response `content` was empty and `reasoning_content` fallback triggered. If this happens repeatedly:
- Reduce `SARVAM_MAX_TOKENS`
- Check the prompt is under 2000 chars
- Retry with different chapter selection

**Problem:** Question paper generation is slow (2–3 minutes).
**Cause:** Sarvam-105b × 4 sections × 4000 tokens is sequential.
**Fix:** Switch `SARVAM_MODEL=sarvam-30b` (faster, less accurate) if speed matters more than depth.

### 22.4 Media & uploads

**Problem:** Uploaded topper photo shows broken image icon on login page.
**Cause:** `DEBUG=False` — Django's `static()` helper doesn't serve media.
**Fix:** Ensure `SERVE_MEDIA_LOCALLY=True` in `.env` OR configure IIS/nginx to serve `/media/` directly.

**Problem:** "Image is too large (decompression bomb)."
**Cause:** Uploaded image exceeds 25 million pixels.
**Fix:** Resize the source image below 25MP before upload.

**Problem:** "The uploaded file is not a valid image."
**Cause:** File extension doesn't match content (magic-byte check failed). Common cause: file was renamed from `.txt` to `.jpg`.
**Fix:** Use a real image file.

### 22.5 Deployment (Windows IIS)

**Problem:** `DisallowedHost` error.
**Fix:** Add the server IP / hostname to `ALLOWED_HOSTS` in `.env`:
```
ALLOWED_HOSTS=10.1.2.3,padhaiwithai.raj.gov.in,localhost
```

**Problem:** Static files return 404 on IIS.
**Fix:**
1. `python manage.py collectstatic --noinput`
2. Confirm `staticfiles/` directory is in the IIS site path
3. Restart IIS: `iisreset` (from admin PowerShell)

**Problem:** wfastcgi.log fills up disk.
**Fix:** Rotate logs weekly via Task Scheduler, or reduce log level in `settings.py`:
```python
LOGGING = { 'root': { 'level': 'WARNING' } }
```

### 22.6 Data

**Problem:** Collector dashboard shows 0 tests.
**Cause:** Old tests have `district = NULL`.
**Fix:**
```bash
python manage.py shell
```
```python
from school_app.models import Test, District
d = District.objects.get(name_english='Tonk')
Test.objects.filter(district__isnull=True).update(district=d)
```

**Problem:** Session expires too quickly.
**Fix:** Increase in `settings.py`:
```python
SESSION_COOKIE_AGE = 60 * 60  # 1 hour
```

### 22.7 Dropbox backup

**Problem:** Backup fails with "Token expired."
**Fix:** Dropbox short-lived tokens expire in 4 hours. Get a **long-lived token** from the App Console:
1. App Console → your app → Settings tab
2. "Generated access token" — click **Generate**
3. This is long-lived (default). Copy to `.env`.

Or configure OAuth2 refresh flow (complex; contact developer).

---

## 23. Appendix — URL Reference

### Admin & auth

| URL | Access | Purpose |
|---|---|---|
| `/login/` | All admin roles | Admin login |
| `/student-login/` | Students | Student login |
| `/logout/` | Any logged-in | Logout (kills all sessions) |
| `/student-logout/` | Students | Student logout |
| `/change-password/` | Admin users | Admin password change |
| `/student-change-password/` | Students | Student password change (with captcha) |
| `/admin/` | System Admin | Django admin panel |

### Dashboards

| URL | Access | Purpose |
|---|---|---|
| `/` or `/dashboard/` | Any admin | Role-based redirect |
| `/system-admin-dashboard/` | System Admin | Overall system view |
| `/state-dashboard/` | State Admin | State-level overview |
| `/collector-dashboard/` | District/State/System | District Collector view |
| `/block-dashboard/` | Block Admin | Block overview |
| `/student-dashboard/` | Students | Student home |
| `/analysis-dashboard/` | Any admin | Per-student analysis |
| `/report-dashboard/` | District Admin | Aggregated reports |

### Hierarchy management

| URL | Access | Purpose |
|---|---|---|
| `/manage/states/` | System Admin | List states |
| `/create-state/` | System Admin | Create state |
| `/manage/districts/` | State Admin | List districts |
| `/create-district/` | State Admin | Create district |
| `/manage/blocks/` | District Admin | List blocks |
| `/create-block/` | District Admin | Create block |
| `/manage/schools/` | District/Block Admin | List schools (with NIC code + pagination) |
| `/create-school-manage/` | District/Block Admin | Create school |

### Tests & marks

| URL | Access | Purpose |
|---|---|---|
| `/add-test/` | District Admin | Create test |
| `/activate-test/<id>/` | District Admin | Activate/deactivate |
| `/marks/` | School Admin | Marks list |
| `/marks/add/` | School Admin | Add marks (individual) |
| `/test-marks-entry/<id>/` | School Admin | Bulk marks grid |
| `/view-test-results/<id>/` | Any admin | Test result view (sortable) |
| `/upload-student-data/` | School/District Admin | Bulk student upload |

### AI features (admin)

| URL | Access | Purpose |
|---|---|---|
| `/question-paper/` | District/School Admin | AI paper generator |
| `/question-paper-history/` | Same | Generated paper history |
| `/assign-paper/<id>/` | Same | Assign paper to class |
| `/omr-upload/` | School Admin | Upload OMR sheets |
| `/omr-confirm/<id>/` | School Admin | Confirm OMR detections |
| `/download-omr-sheets/<id>/` | School Admin | Get printable OMR PDF |

### Toppers

| URL | Access | Purpose |
|---|---|---|
| `/district/toppers/` | District Admin | List toppers |
| `/district/toppers/upload/` | District Admin | Upload topper |
| `/district/toppers/<pk>/edit/` | District Admin | Edit topper |
| `/district/toppers/<pk>/toggle/` | District Admin | Show/hide |
| `/district/toppers/<pk>/delete/` | District Admin | Delete |

### Calendar

| URL | Access | Purpose |
|---|---|---|
| `/academic-calendar/` | Any logged-in | View calendar |
| `/academic-calendar/manage/` | District Admin | Manage events |
| `/academic-calendar/add/` (POST) | District Admin | AJAX add |
| `/academic-calendar/delete/<id>/` (POST) | District Admin | AJAX delete |

### AI Sathi

| URL | Access | Purpose |
|---|---|---|
| `/ai_sathi/` | Any logged-in | Chatbot main page |
| `/ai_sathi/chat/` (POST) | Any logged-in | Send message |
| `/ai_sathi/clear/` (POST) | Any logged-in | New chat |
| `/ai_sathi/change-chapter/` (POST) | Any logged-in | Switch chapter |
| `/ai_sathi/starters/` | Any logged-in | Get starter questions |
| `/ai_sathi/subjects/`, `/ai_sathi/chapters/` | Any logged-in | Dropdown data |
| `/manage-classes/`, `/manage-subjects/`, `/manage-chapters/` | State Admin | Curriculum admin |

### Student features

| URL | Access | Purpose |
|---|---|---|
| `/student-tests/` | Students | Available tests |
| `/student-view-test/<id>/` | Students | Take test |
| `/student-performance/` | Students | Performance details |
| `/student-practice-test/` | Students | Practice tests |
| `/student-recommendations/` | Students | Video suggestions |
| `/student-doubt-solver/` | Students | Photo-based doubt solver |
| `/student-video-learning/` | Students | Video learning |
| `/student-assigned-papers/` | Students | Assigned papers |
| `/take-paper/<id>/` | Students | Take assigned paper |
| `/math-tools/` | **All admin roles + Students** | Math solver + question generator (Sarvam & GPT engines) |
| `/ask-pai/` | **All admin roles + Students** | Single-question math AI (photo input supported) |
| `/solve-math/` (POST) | Same | Submit selected questions for AI solving |
| `/generate-math/` (POST) | Same | Generate AI questions |
| `/solve-again/` (POST) | Same | Rewrite solution in simpler language |

### Reports

| URL | Access | Purpose |
|---|---|---|
| `/school-report/` | Various | School report |
| `/student-report/` | Various | Student report |
| `/school-ranking/` | Various | School rankings |
| `/student-ranking/` | Various | Student rankings |
| `/top-students/` | Various | Top students list |
| `/weakest-students/` | Various | Bottom students |
| `/schools-without-tests/` | District Admin | Compliance check |
| `/schools-without-students/` | District Admin | Empty schools |

### Attendance

| URL | Access | Purpose |
|---|---|---|
| `/submit-attendance/` | School Admin | Daily entry |
| `/attendance-summary/` | School Admin | School summary |
| `/school-daily-attendance-summary/` | School Admin | Daily grid |
| `/block-attendance-report/` | Block Admin | Block report |
| `/block-wise-attendance-summary/` | District Admin | Block roll-up |
| `/district-wise-attendance-summary/` | State/System | District roll-up |
| `/date-wise-attendance-summary/` | Various | By date |

### Activity & audit

| URL | Access | Purpose |
|---|---|---|
| `/activity-logs/` | District Admin | Audit trail |

---

## Document History

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | March 2026 | Original team | First deployment manual |
| 2.0 | July 2026 | Development team | Full rewrite: added AI Sathi, Question Paper Generator, OMR, Assigned Papers, Toppers, Academic Calendar, Analysis Dashboard, updated security section for V-01 through V-25 fixes, added student portal guide, added 30+ screenshot placeholders. |
| 2.1 | July 2026 | Development team | Added Section 17A "Math Tools (Teacher & Admin)" — clarified that Math Tools is accessible from School / Block / District / State / System dashboards, not just Student portal. Documented Sarvam vs GPT engine choice, Solve Again feature, PDF export, content bank JSON schema. Added 3 new screenshot placeholders. |

---

## Screenshots to Capture (Reference Checklist)

Save all screenshots to `docs/screenshots/` with the filenames referenced throughout this manual. Suggested capture list:

- [ ] `01_hierarchy_overview.png` — visual of 5-level hierarchy
- [ ] `04_env_files.png` — sample .env showing key fields
- [ ] `05_migrations_success.png` — successful `migrate` output
- [ ] `06a_manage_states.png` — states list
- [ ] `06b_create_district.png` — new district form
- [ ] `06c_manage_schools.png` — schools with NIC code column
- [ ] `07_login_page.png` — admin login with captcha
- [ ] `08a_upload_students.png` — Excel upload form
- [ ] `08b_sample_excel.png` — sample .xlsx layout
- [ ] `09a_add_test.png` — test creation form
- [ ] `09b_marks_entry.png` — bulk marks grid
- [ ] `10_collector_dashboard.png` — full dashboard
- [ ] `11a_qp_form.png` — question paper form
- [ ] `11b_qp_preview.png` — generated paper
- [ ] `11c_qp_history.png` — history list
- [ ] `12a_assign_paper.png` — assign paper dialog
- [ ] `12b_omr_sheet.png` — printable OMR
- [ ] `12c_omr_review.png` — post-scan review
- [ ] `13a_calendar_manage.png` — calendar management
- [ ] `13b_calendar_public.png` — read-only calendar
- [ ] `14a_topper_list.png` — topper grid
- [ ] `14b_topper_upload.png` — upload form
- [ ] `14c_login_toppers.png` — login page ticker
- [ ] `15_manage_chapters.png` — chapter admin
- [ ] `16a_analysis.png` — analysis dashboard
- [ ] `16b_activity_logs.png` — activity log filters
- [ ] `17_attendance.png` — attendance entry
- [ ] `17A_math_tools.png` — Math Tools main (Sarvam engine selected)
- [ ] `17A_math_solutions.png` — LaTeX-rendered solutions
- [ ] `17A_ask_pai.png` — Ask PAI single-question view
- [ ] `18a_student_dashboard.png` — student home
- [ ] `18b_ai_sathi.png` — AI Sathi chat interface
- [ ] `18c_math_tools.png` — math solver
- [ ] `18d_practice_test.png` — practice test in progress

*33 screenshots total. Estimated capture time: ~2.5 hours.*

---

*End of manual · v2.0 · July 2026 · [contact-email@rajasthan.gov.in]*
