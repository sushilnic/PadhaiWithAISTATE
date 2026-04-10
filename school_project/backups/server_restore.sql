-- ============================================================
-- PadhaiWithAI - Server Restore / Sync SQL Script
-- Run this on the production server after deploying new code
-- Date: 2026-02-18
-- ============================================================

-- ============================================================
-- STEP 1: Fake-migrate missing migrations (schema already exists)
-- Run these Django commands instead of SQL:
--
--   python manage.py migrate school_app 0011_state_model --fake
--   python manage.py migrate school_app 0012_add_student_auth_fields --fake
--   python manage.py migrate school_app 0013_practicetest --fake
--   python manage.py migrate school_app 0014_alter_practicetest_topic --fake
--   python manage.py migrate school_app 0015_add_management_fields --fake
--
-- OR run this SQL directly to mark them as applied:
-- ============================================================

INSERT INTO django_migrations (app, name, applied)
SELECT 'school_app', '0011_state_model', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app = 'school_app' AND name = '0011_state_model');

INSERT INTO django_migrations (app, name, applied)
SELECT 'school_app', '0012_add_student_auth_fields', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app = 'school_app' AND name = '0012_add_student_auth_fields');

INSERT INTO django_migrations (app, name, applied)
SELECT 'school_app', '0013_practicetest', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app = 'school_app' AND name = '0013_practicetest');

INSERT INTO django_migrations (app, name, applied)
SELECT 'school_app', '0014_alter_practicetest_topic', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app = 'school_app' AND name = '0014_alter_practicetest_topic');

INSERT INTO django_migrations (app, name, applied)
SELECT 'school_app', '0015_add_management_fields', NOW()
WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app = 'school_app' AND name = '0015_add_management_fields');


-- ============================================================
-- STEP 2: Verify schema exists (run these checks, should return rows)
-- If any column is missing, the schema needs to be created first
-- ============================================================

-- Check student auth columns exist
SELECT column_name FROM information_schema.columns
WHERE table_name = 'school_app_student'
AND column_name IN ('password', 'is_active', 'last_login');

-- Check state table exists
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'school_app_state');

-- Check practicetest table exists
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'school_app_practicetest');

-- Check district/block/school have is_active, created_at
SELECT column_name FROM information_schema.columns
WHERE table_name = 'school_app_district' AND column_name IN ('is_active', 'created_at');

SELECT column_name FROM information_schema.columns
WHERE table_name = 'school_app_block' AND column_name IN ('is_active', 'created_at');

SELECT column_name FROM information_schema.columns
WHERE table_name = 'school_app_school' AND column_name = 'is_active';


-- ============================================================
-- STEP 3: Hash all plain text student passwords
-- Plain text passwords don't start with 'pbkdf2_sha256$'
-- This CANNOT be done via SQL (Django uses PBKDF2 with random salt)
-- Run this Django management command instead:
--
--   python manage.py hash_student_passwords
--
-- (See hash_student_passwords.py management command created below)
-- ============================================================


-- ============================================================
-- STEP 4: Set defaults for any NULL fields after restore
-- ============================================================

-- Ensure all students have is_active = true if NULL
UPDATE school_app_student SET is_active = TRUE WHERE is_active IS NULL;

-- Ensure all districts have is_active = true if NULL
UPDATE school_app_district SET is_active = TRUE WHERE is_active IS NULL;

-- Ensure all blocks have is_active = true if NULL
UPDATE school_app_block SET is_active = TRUE WHERE is_active IS NULL;

-- Ensure all schools have is_active = true if NULL
UPDATE school_app_school SET is_active = TRUE WHERE is_active IS NULL;


-- ============================================================
-- STEP 5: Quick data integrity checks
-- ============================================================

-- Count students with plain text passwords (should be 0 after Step 3)
SELECT COUNT(*) AS plain_text_passwords
FROM school_app_student
WHERE password IS NOT NULL
  AND password != ''
  AND password NOT LIKE 'pbkdf2_sha256$%';

-- Count total students
SELECT COUNT(*) AS total_students FROM school_app_student;

-- Check orphan students (no school)
SELECT COUNT(*) AS orphan_students
FROM school_app_student s
LEFT JOIN school_app_school sch ON s.school_id = sch.id
WHERE sch.id IS NULL;

-- Check orphan marks (no student or test)
SELECT COUNT(*) AS orphan_marks
FROM school_app_marks m
LEFT JOIN school_app_student s ON m.student_id = s.id
LEFT JOIN school_app_test t ON m.test_id = t.test_number
WHERE s.id IS NULL OR t.test_number IS NULL;
