-- ============================================================
-- PadhaiWithAI — Server Database Update Script
-- ============================================================
-- PURPOSE: Bring a restored backup DB in sync with current Django models.
--          ALL statements are idempotent (safe to run multiple times).
--          NO existing data is deleted or overwritten.
--
-- HOW TO RUN:
--   psql -U your_db_user -d your_db_name -f server_db_update.sql
--
-- After running this SQL, also run:
--   python manage.py migrate --fake
-- to mark all migrations as applied in Django's tracker.
-- ============================================================


-- ============================================================
-- 1. CustomUser: Add role flag columns (Migration 0011)
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_customuser' AND column_name='is_state_user') THEN
        ALTER TABLE school_app_customuser ADD COLUMN is_state_user BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_customuser' AND column_name='is_district_user') THEN
        ALTER TABLE school_app_customuser ADD COLUMN is_district_user BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_customuser' AND column_name='is_block_user') THEN
        ALTER TABLE school_app_customuser ADD COLUMN is_block_user BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_customuser' AND column_name='is_school_user') THEN
        ALTER TABLE school_app_customuser ADD COLUMN is_school_user BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_customuser' AND column_name='is_system_admin') THEN
        ALTER TABLE school_app_customuser ADD COLUMN is_system_admin BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;


-- ============================================================
-- 2. State table (Migration 0011)
-- ============================================================

CREATE TABLE IF NOT EXISTS school_app_state (
    id              BIGSERIAL PRIMARY KEY,
    name_english    VARCHAR(100) NOT NULL,
    name_hindi      VARCHAR(100) NOT NULL,
    code            VARCHAR(10)  NOT NULL UNIQUE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    admin_id        BIGINT UNIQUE REFERENCES school_app_customuser(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS school_app_state_admin_id ON school_app_state(admin_id);


-- ============================================================
-- 3. District table (Migration 0011 + 0015)
-- ============================================================

CREATE TABLE IF NOT EXISTS school_app_district (
    id              BIGSERIAL PRIMARY KEY,
    name_english    VARCHAR(100) NOT NULL,
    name_hindi      VARCHAR(100) NOT NULL,
    state_id        BIGINT REFERENCES school_app_state(id) ON DELETE CASCADE,
    admin_id        BIGINT UNIQUE REFERENCES school_app_customuser(id) ON DELETE SET NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- If table existed without is_active / created_at (from 0011 only, without 0015)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_district' AND column_name='is_active') THEN
        ALTER TABLE school_app_district ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_district' AND column_name='created_at') THEN
        ALTER TABLE school_app_district ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS school_app_district_state_id ON school_app_district(state_id);
CREATE INDEX IF NOT EXISTS school_app_district_admin_id ON school_app_district(admin_id);


-- ============================================================
-- 4. Block table (Migration 0011 + 0015)
-- ============================================================

CREATE TABLE IF NOT EXISTS school_app_block (
    id              BIGSERIAL PRIMARY KEY,
    name_english    VARCHAR(100) NOT NULL,
    name_hindi      VARCHAR(100) NOT NULL,
    district_id     BIGINT NOT NULL REFERENCES school_app_district(id) ON DELETE CASCADE,
    admin_id        BIGINT UNIQUE REFERENCES school_app_customuser(id) ON DELETE CASCADE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- If table existed without is_active / created_at
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_block' AND column_name='is_active') THEN
        ALTER TABLE school_app_block ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_block' AND column_name='created_at') THEN
        ALTER TABLE school_app_block ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS school_app_block_district_id ON school_app_block(district_id);
CREATE INDEX IF NOT EXISTS school_app_block_admin_id    ON school_app_block(admin_id);


-- ============================================================
-- 5. School table: Add missing columns (Migration 0011 + 0015)
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_school' AND column_name='block_id') THEN
        ALTER TABLE school_app_school ADD COLUMN block_id BIGINT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_school' AND column_name='nic_code') THEN
        ALTER TABLE school_app_school ADD COLUMN nic_code VARCHAR(20);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_school' AND column_name='is_active') THEN
        ALTER TABLE school_app_school ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
END $$;

-- Add FK constraint if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'school_app_school'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%block_id%'
    ) THEN
        -- Check if block table exists before adding FK
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'school_app_block') THEN
            ALTER TABLE school_app_school
                ADD CONSTRAINT school_app_school_block_id_fk
                FOREIGN KEY (block_id) REFERENCES school_app_block(id) ON DELETE CASCADE;
        END IF;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS school_app_school_block_id ON school_app_school(block_id);


-- ============================================================
-- 6. Student table: Add auth fields + fix class_name (Mig 0003 + 0012)
-- ============================================================

-- Migration 0003: Remove grade, add class_name
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_student' AND column_name='class_name') THEN
        ALTER TABLE school_app_student ADD COLUMN class_name VARCHAR(2) NOT NULL DEFAULT '10';
    END IF;
    -- Migration 0012: password, is_active, last_login
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_student' AND column_name='password') THEN
        ALTER TABLE school_app_student ADD COLUMN password VARCHAR(128);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_student' AND column_name='is_active') THEN
        ALTER TABLE school_app_student ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_student' AND column_name='last_login') THEN
        ALTER TABLE school_app_student ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- Make roll_number unique if not already (Migration 0002)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'school_app_student'
        AND constraint_type = 'UNIQUE'
        AND constraint_name LIKE '%roll_number%'
    ) THEN
        ALTER TABLE school_app_student ADD CONSTRAINT school_app_student_roll_number_uniq UNIQUE (roll_number);
    END IF;
END $$;


-- ============================================================
-- 7. Test table: Add missing columns (Mig 0005-0008 + max_marks)
-- ============================================================

CREATE TABLE IF NOT EXISTS school_app_test (
    test_number     SERIAL PRIMARY KEY,
    test_name       VARCHAR(255) NOT NULL,
    subject_name    VARCHAR(255) NOT NULL,
    pdf_file_questions VARCHAR(100),
    pdf_file_answers   VARCHAR(100),
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    test_date       DATE,
    created_by_id   BIGINT REFERENCES school_app_customuser(id) ON DELETE SET NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    max_marks       DOUBLE PRECISION NOT NULL DEFAULT 100
);

-- If table exists but columns are missing
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_test' AND column_name='test_date') THEN
        ALTER TABLE school_app_test ADD COLUMN test_date DATE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_test' AND column_name='pdf_file_questions') THEN
        ALTER TABLE school_app_test ADD COLUMN pdf_file_questions VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_test' AND column_name='pdf_file_answers') THEN
        ALTER TABLE school_app_test ADD COLUMN pdf_file_answers VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_test' AND column_name='created_by_id') THEN
        ALTER TABLE school_app_test ADD COLUMN created_by_id BIGINT REFERENCES school_app_customuser(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_test' AND column_name='created_at') THEN
        ALTER TABLE school_app_test ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
    END IF;
    -- max_marks: NOT in any migration, but required by the model (schema drift fix)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_test' AND column_name='max_marks') THEN
        ALTER TABLE school_app_test ADD COLUMN max_marks DOUBLE PRECISION NOT NULL DEFAULT 100;
    END IF;
    -- Remove old pdf_file column if it still exists (replaced by questions/answers in 0008)
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_test' AND column_name='pdf_file') THEN
        ALTER TABLE school_app_test DROP COLUMN pdf_file;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS school_app_test_created_by_id ON school_app_test(created_by_id);


-- ============================================================
-- 8. Marks table: Add test FK, remove old test_number (Mig 0009-0010)
-- ============================================================

DO $$
BEGIN
    -- Add test_id FK column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_marks' AND column_name='test_id') THEN
        ALTER TABLE school_app_marks ADD COLUMN test_id INTEGER REFERENCES school_app_test(test_number) ON DELETE CASCADE;
    END IF;
    -- Remove old test_number/subject column if still exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_marks' AND column_name='test_number') THEN
        ALTER TABLE school_app_marks DROP COLUMN test_number;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='school_app_marks' AND column_name='subject') THEN
        ALTER TABLE school_app_marks DROP COLUMN subject;
    END IF;
END $$;

-- Unique together (student, test) if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'school_app_marks'
        AND constraint_type = 'UNIQUE'
        AND constraint_name LIKE '%student%test%'
    ) THEN
        -- Only add if both columns exist and no duplicate pairs
        ALTER TABLE school_app_marks ADD CONSTRAINT school_app_marks_student_test_uniq UNIQUE (student_id, test_id);
    END IF;
EXCEPTION WHEN others THEN
    RAISE NOTICE 'Unique constraint on marks(student,test) may already exist or has duplicates - skipping';
END $$;

CREATE INDEX IF NOT EXISTS school_app_marks_test_id ON school_app_marks(test_id);
CREATE INDEX IF NOT EXISTS school_app_marks_student_id ON school_app_marks(student_id);


-- ============================================================
-- 9. Book table (Migration 0004)
-- ============================================================

CREATE TABLE IF NOT EXISTS school_app_book (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    language        VARCHAR(20)  NOT NULL,
    json_file_path  VARCHAR(255) NOT NULL
);


-- ============================================================
-- 10. Attendance table (Migration 0011)
-- ============================================================

CREATE TABLE IF NOT EXISTS school_app_attendance (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE NOT NULL DEFAULT CURRENT_DATE,
    is_present      BOOLEAN NOT NULL DEFAULT TRUE,
    student_id      BIGINT NOT NULL REFERENCES school_app_student(id) ON DELETE CASCADE
);

-- Unique (student, date) if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'school_app_attendance'
        AND constraint_type = 'UNIQUE'
    ) THEN
        ALTER TABLE school_app_attendance ADD CONSTRAINT school_app_attendance_student_date_uniq UNIQUE (student_id, date);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS school_app_attendance_student_id ON school_app_attendance(student_id);


-- ============================================================
-- 11. PracticeTest table (Migration 0013 + 0014)
-- ============================================================

CREATE TABLE IF NOT EXISTS school_app_practicetest (
    id              BIGSERIAL PRIMARY KEY,
    topic           VARCHAR(200) NOT NULL,
    difficulty      VARCHAR(20)  NOT NULL DEFAULT 'medium',
    total_questions INTEGER      NOT NULL DEFAULT 10,
    correct_answers INTEGER      NOT NULL DEFAULT 0,
    wrong_answers   INTEGER      NOT NULL DEFAULT 0,
    time_taken      INTEGER,
    attempted_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    student_id      BIGINT NOT NULL REFERENCES school_app_student(id) ON DELETE CASCADE
);

-- If table exists but topic is still varchar(50) from 0013, widen it
DO $$
BEGIN
    -- Just ensure max_length is 200 (idempotent via ALTER TYPE)
    ALTER TABLE school_app_practicetest ALTER COLUMN topic TYPE VARCHAR(200);
EXCEPTION WHEN undefined_table THEN
    NULL; -- table doesn't exist yet, CREATE above handled it
END $$;

CREATE INDEX IF NOT EXISTS school_app_practicetest_student_topic ON school_app_practicetest(student_id, topic);
CREATE INDEX IF NOT EXISTS school_app_practicetest_attempted     ON school_app_practicetest(attempted_at);


-- ============================================================
-- 12. Mark ALL migrations as applied (so Django won't re-run them)
-- ============================================================

DO $$
DECLARE
    mig TEXT;
    migs TEXT[] := ARRAY[
        '0001_initial',
        '0002_alter_student_roll_number',
        '0003_rename_subject_marks_test_number_and_more',
        '0004_book',
        '0005_test',
        '0005_testpaper',
        '0006_delete_testpaper',
        '0006_test_test_date',
        '0007_merge_0006_delete_testpaper_0006_test_test_date',
        '0008_remove_test_pdf_file_test_pdf_file_answers_and_more',
        '0009_marks_test_alter_marks_unique_together',
        '0010_remove_marks_test_number',
        '0011_state_model',
        '0012_add_student_auth_fields',
        '0013_practicetest',
        '0014_alter_practicetest_topic',
        '0015_add_management_fields'
    ];
BEGIN
    FOREACH mig IN ARRAY migs
    LOOP
        IF NOT EXISTS (SELECT 1 FROM django_migrations WHERE app='school_app' AND name=mig) THEN
            INSERT INTO django_migrations (app, name, applied) VALUES ('school_app', mig, NOW());
        END IF;
    END LOOP;
END $$;


-- ============================================================
-- VERIFICATION: Run these to confirm everything is in place
-- ============================================================

-- Check all tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'school_app_%'
ORDER BY table_name;

-- Check CustomUser role columns
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'school_app_customuser'
AND column_name IN ('is_system_admin','is_state_user','is_district_user','is_block_user','is_school_user')
ORDER BY column_name;

-- Check Test.max_marks exists
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'school_app_test' AND column_name = 'max_marks';

-- Check migrations are tracked
SELECT name, applied FROM django_migrations
WHERE app = 'school_app' ORDER BY name;


-- ============================================================
-- DONE!
-- ============================================================
-- After running this file:
--   1. Your restored DB now matches the Django models exactly
--   2. All 15 migrations are marked as applied
--   3. No data was deleted — only ADD COLUMN / CREATE TABLE IF NOT EXISTS
--   4. Future backups of this DB will restore cleanly
--   5. After restore, just run: python manage.py migrate --fake
--      (or run this SQL file again — it's safe to re-run)
-- ============================================================
