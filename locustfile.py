"""
Locust load-testing plan for PadhaiWithAI.

──────────────────────────────────────────────────────────────────────────
INSTALL
    pip install locust

RUN (headless — for CI / one-shot benchmarks)
    locust -f locustfile.py --host http://10.138.241.9:8080 \\
           -u 100 -r 10 -t 5m --headless \\
           --csv=loadtest_report

    -u  = simultaneous virtual users (ramp target)
    -r  = users spawned per second (ramp rate)
    -t  = test duration
    --csv writes stats CSVs you can commit for baseline comparisons.

RUN (interactive UI — for exploring bottlenecks)
    locust -f locustfile.py --host http://10.138.241.9:8080
    # then open http://localhost:8089

CREDENTIALS
    Test users must exist on the target server. Export before running:
        set LOCUST_SCHOOL_EMAIL=school_test@padhaiwithai.local
        set LOCUST_SCHOOL_PASS=changeme
        set LOCUST_STUDENT_ROLL=999999999999
        set LOCUST_STUDENT_PASS=1234
    (Windows: use `set`. macOS/Linux: `export`.)

WHAT THIS TESTS
    - Anonymous public endpoints  (home, login pages, static)
    - Logged-in school-admin flow (dashboard, students, marks, reports)
    - Logged-in student flow      (dashboard, practice progress)
    - Read-heavy reports          (block-wise summary, per-school counts)

WHAT THIS INTENTIONALLY DOES NOT TEST
    - Sarvam AI endpoints          — costs real money per call
    - POST endpoints that mutate  — would pollute prod data
    - Sending real emails         — obvious reason
    - PDF generation flows         — extremely CPU-heavy, would DOS your own server

    Uncomment blocks marked  #  ACTIVATE FOR MUTATION-SAFE STAGING ONLY
    only when running against a scratch DB / staging environment.

READING THE RESULTS
    Focus on the p95 and failure rate:
      p95 <  200 ms   → fast
      p95 <  500 ms   → acceptable
      p95 < 1000 ms   → slow, dig in
      p95 > 1000 ms   → optimize (indexes, caching, CDN)

    Any endpoint with > 1% failure rate is a bug — investigate.
──────────────────────────────────────────────────────────────────────────
"""

import os
import random
import re

from locust import HttpUser, task, between, events


# ── Configurable via environment variables ─────────────────────────────
SCHOOL_EMAIL   = os.getenv("LOCUST_SCHOOL_EMAIL",   "school_test@padhaiwithai.local")
SCHOOL_PASS    = os.getenv("LOCUST_SCHOOL_PASS",    "changeme")
STUDENT_ROLL   = os.getenv("LOCUST_STUDENT_ROLL",   "999999999999")
STUDENT_PASS   = os.getenv("LOCUST_STUDENT_PASS",   "1234")

CSRF_RE = re.compile(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)')


def _extract_csrf(html):
    """Pull the CSRF token out of a rendered form. Returns None if not found."""
    m = CSRF_RE.search(html)
    return m.group(1) if m else None


# ═══════════════════════════════════════════════════════════════════════
# Anonymous visitor — highest weight (real traffic is mostly this)
# ═══════════════════════════════════════════════════════════════════════
class AnonymousVisitor(HttpUser):
    """Simulates the login-page-and-away user: 60% of your real traffic."""
    weight = 5
    wait_time = between(2, 5)

    @task(4)
    def home(self):
        self.client.get("/", name="/  (home)")

    @task(2)
    def login_page(self):
        self.client.get("/login/", name="/login/")

    @task(2)
    def student_login_page(self):
        self.client.get("/student/login/", name="/student/login/")

    @task(1)
    def ai_sathi_page(self):
        # Public landing view (unauthenticated visitors get a login prompt)
        self.client.get("/ai_sathi/", name="/ai_sathi/")

    @task(3)
    def logo_static(self):
        # Simulates real browsers pulling the logo. Should hit whitenoise cache.
        self.client.get(
            "/static/school_app/images/pailogo.png",
            name="/static/pailogo.png",
        )

    @task(1)
    def favicon(self):
        # Test the redirect route we added earlier
        self.client.get("/favicon.ico", name="/favicon.ico  (redirect)")


# ═══════════════════════════════════════════════════════════════════════
# Logged-in school admin — read-heavy, safest to exercise
# ═══════════════════════════════════════════════════════════════════════
class SchoolAdminUser(HttpUser):
    """Simulates a school admin browsing dashboards + reports (READ ONLY)."""
    weight = 3
    wait_time = between(3, 8)

    def on_start(self):
        """Log in once per virtual user. If login fails, this user does nothing."""
        # 1. GET the login page to seed a CSRF cookie + capture the token
        resp = self.client.get("/login/", name="/login/  (bootstrap)")
        token = _extract_csrf(resp.text)
        if not token:
            events.request.fire(
                request_type="LOGIN",
                name="csrf_bootstrap",
                response_time=0, response_length=0,
                exception=RuntimeError("Could not extract CSRF token from /login/"),
            )
            self.environment.runner.quit()
            return

        # 2. POST credentials — captcha is skipped in test env? If your dev env
        #    requires captcha, disable it via settings for load-testing only,
        #    OR extract captcha_0 + captcha_1 from the login form (see docs).
        resp = self.client.post(
            "/login/",
            data={
                "csrfmiddlewaretoken": token,
                "identifier": SCHOOL_EMAIL,
                "password":   SCHOOL_PASS,
                # If your CAPTCHA is required, add:
                # "captcha_0": captcha_hash,   (parse from form)
                # "captcha_1": captcha_answer, (impossible without OCR — disable captcha for test env)
            },
            allow_redirects=True,
            name="POST /login/",
        )
        if "/dashboard/" not in resp.url and "dashboard" not in resp.url:
            self.environment.runner.quit()

    @task(3)
    def dashboard(self):
        self.client.get("/dashboard/", name="/dashboard/  (school)")

    @task(2)
    def students_list(self):
        self.client.get("/studentslist/", name="/studentslist/  (page 1)")

    @task(1)
    def students_list_page2(self):
        self.client.get("/studentslist/?page=2", name="/studentslist/  (page 2)")

    @task(1)
    def students_search(self):
        # Exercises the LIKE query path
        q = random.choice(["kum", "shar", "priy", "1023"])
        self.client.get(f"/studentslist/?q={q}", name="/studentslist/  (search)")

    @task(2)
    def marks_list(self):
        self.client.get("/marks/", name="/marks/")

    @task(1)
    def analysis_dashboard(self):
        self.client.get("/analysis-dashboard/", name="/analysis-dashboard/")

    @task(1)
    def attendance_summary(self):
        self.client.get("/attendance/summary/", name="/attendance/summary/")

    @task(1)
    def test_average(self):
        self.client.get("/test-average/", name="/test-average/")

    @task(1)
    def block_wise_summary(self):
        # (District-scoped; harmless for school user, may 403 — good to measure that too)
        self.client.get("/report/block-wise-summary/", name="/report/block-wise-summary/")


# ═══════════════════════════════════════════════════════════════════════
# Logged-in student — mobile-heavy, hit the practice-progress endpoints
# ═══════════════════════════════════════════════════════════════════════
class StudentUser(HttpUser):
    """Simulates a student on the mobile portal."""
    weight = 2
    wait_time = between(4, 10)

    def on_start(self):
        resp = self.client.get("/student/login/", name="/student/login/  (bootstrap)")
        token = _extract_csrf(resp.text)
        if not token:
            self.environment.runner.quit()
            return

        # Student login uses roll_number + password + captcha.
        # Real load test needs captcha disabled in the test env
        # (see LOCUST_STUDENT_CAPTCHA_ANSWER env or disable in settings).
        resp = self.client.post(
            "/student/login/",
            data={
                "csrfmiddlewaretoken": token,
                "roll_number": STUDENT_ROLL,
                "password":    STUDENT_PASS,
            },
            allow_redirects=True,
            name="POST /student/login/",
        )
        if "student" not in resp.url:
            self.environment.runner.quit()

    @task(3)
    def student_dashboard(self):
        self.client.get("/student/dashboard/", name="/student/dashboard/")

    @task(2)
    def performance(self):
        self.client.get("/student/performance/", name="/student/performance/")

    @task(1)
    def practice_progress(self):
        self.client.get("/student/practice-progress/", name="/student/practice-progress/")

    @task(1)
    def tests_available(self):
        self.client.get("/student/tests/", name="/student/tests/")


# ═══════════════════════════════════════════════════════════════════════
# Report burner — hits the slow queries hard to find missing indexes
# ═══════════════════════════════════════════════════════════════════════
class HeavyReportsUser(HttpUser):
    """Small population, hammering the most expensive read paths.

    Use this to identify N+1 queries, missing indexes, and endpoints that
    don't cache. In production this weight should be low (1) — you want
    the mix to reflect real traffic. Bump temporarily when hunting perf bugs.
    """
    weight = 1
    wait_time = between(1, 3)

    def on_start(self):
        resp = self.client.get("/login/", name="/login/  (heavy bootstrap)")
        token = _extract_csrf(resp.text)
        if not token:
            self.environment.runner.quit()
            return
        self.client.post(
            "/login/",
            data={
                "csrfmiddlewaretoken": token,
                "identifier": SCHOOL_EMAIL,
                "password":   SCHOOL_PASS,
            },
            allow_redirects=True,
            name="POST /login/  (heavy)",
        )

    @task
    def block_wise_summary(self):
        self.client.get("/report/block-wise-summary/", name="[H] block-wise-summary")

    @task
    def schools_with_student_counts(self):
        self.client.get("/report/schools-with-student-counts/", name="[H] schools-with-student-counts")

    @task
    def schools_without_tests(self):
        self.client.get("/report/schools-without-tests/", name="[H] schools-without-tests")

    @task
    def test_average(self):
        self.client.get("/test-average/", name="[H] test-average")

    @task
    def historical_analysis(self):
        # Uses raw SQL against the archive tables — slowest read path
        self.client.get("/historical-analysis/", name="[H] historical-analysis")


# ═══════════════════════════════════════════════════════════════════════
# ACTIVATE FOR MUTATION-SAFE STAGING ONLY
# ═══════════════════════════════════════════════════════════════════════
# The classes below POST data — they will INSERT / UPDATE rows in the DB.
# Never run against production without agreement from stakeholders.
#
# class AttendanceSubmitter(HttpUser):
#     weight = 1
#     wait_time = between(30, 90)
#     def on_start(self):  ...
#     @task
#     def submit_attendance(self):
#         ...  # POST to /attendance/submit/
#
# class QuestionPaperGenerator(HttpUser):
#     """WARNING: each call spends real Sarvam AI credit."""
#     weight = 1
#     wait_time = between(60, 120)
#     ...
