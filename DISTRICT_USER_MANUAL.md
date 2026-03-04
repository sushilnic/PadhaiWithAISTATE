# PadhaiWithAI — District User Manual
### Step-by-Step Guide for New District Setup and Daily Operations

---

## Who This Manual Is For

| User | Role in System | Reads Sections |
|------|---------------|----------------|
| District Collector / DEO | District Admin | All sections |
| Block Education Officer | Block Admin | Section 4, 6, 7 |
| School Principal / HM | School Admin | Section 5, 6, 7 |
| Student | Student | Section 8 |

---

## Table of Contents

1. [Login](#1-login)
2. [District Admin — First Setup](#2-district-admin--first-setup)
3. [District Admin — Daily Operations](#3-district-admin--daily-operations)
4. [Block Admin — Operations](#4-block-admin--operations)
5. [School Admin — Operations](#5-school-admin--operations)
6. [Test Management](#6-test-management)
7. [Marks Entry](#7-marks-entry)
8. [Student Portal](#8-student-portal)
9. [Activity Logs (Audit Trail)](#9-activity-logs-audit-trail)
10. [Account & Password](#10-account--password)

---

## 1. Login

### Admin Login (District / Block / School)
**URL:** `http://your-server/login/`

1. Enter your **Username** and **Password**
2. Enter the **CAPTCHA** (6-character code shown in image)
3. Click **Login**

After login you are taken directly to your role's dashboard.

> **Account locked?** After 5 wrong password attempts the account locks for 30 minutes. Wait or contact your system administrator to unlock.

> **Password expired?** Passwords expire every 90 days. You will be redirected to a change-password screen automatically.

### Student Login
**URL:** `http://your-server/student-login/`

1. Enter **Roll Number**
2. Enter **Password** — default password is **`1234`** (change it after first login)
3. Click **Login**

---

## 2. District Admin — First Setup

Do these steps **once** when setting up the district for the first time. Follow the order exactly.

---

### Step 2.1 — Create Blocks

A Block (विकास खंड) is the administrative unit under a district.

1. Log in as District Admin
2. Click **Manage Blocks** in the top navigation bar
3. Click **Create Block**
4. Fill in:
   - Block name in English
   - Block name in Hindi
   - Admin username (will be the Block Officer's login)
   - Admin password
5. Click **Save**
6. Repeat for every block in your district

> The system automatically assigns this block to your district. You do not need to select the district manually.

---

### Step 2.2 — Create Schools

A School belongs to a Block.

1. Click **Manage Schools** in the top navigation bar
2. Click **Create School**
3. Fill in:
   - School name
   - DISE code (unique government school code)
   - Block — select from dropdown (only blocks in your district appear)
   - School admin username and password
4. Click **Save**
5. Repeat for every school

---

### Step 2.3 — Add Students to Each School

This is done by the **School Admin** (see Section 5.1).
As District Admin you can also upload students for any school.

---

## 3. District Admin — Daily Operations

After first setup, these are the regular tasks.

---

### 3.1 Collector Dashboard

**URL:** `/collector-dashboard/`
**Navbar:** Click **Dashboard**

The dashboard shows four summary cards at the top:

| Card | What It Shows |
|------|--------------|
| Total Schools | Number of schools in your district |
| Total Tests | Tests created for your district |
| Total Students | All enrolled students across the district |
| Active Sessions | Users currently logged in |

Below the cards:

- **Tests Table** — all tests for your district with average marks and score distribution
- **Schools Table** — school-wise performance breakdown
- **Performance Charts** — bar and pie charts showing score bands
- **Previous Year Data** — historical board exam results (if data was loaded)

---

### 3.2 Switching Between Districts (State Admin Only)

If you are a **State Admin** viewing the Collector Dashboard, a **district selector dropdown** appears at the top of the page. Select any district in your state to view its data.

---

## 4. Block Admin — Operations

### 4.1 Login
Use the username and password created by the District Admin.
After login you land on the **Block Dashboard**.

### 4.2 Block Dashboard
Shows:
- List of schools in your block
- Student counts per school
- Test performance summary for block schools

### 4.3 Manage Schools
Block Admin can also create schools within their block:
1. Click **Manage Schools** in navbar
2. Click **Create School** — only blocks belonging to your block's district are shown

---

## 5. School Admin — Operations

### 5.1 Add Students

#### Option A — Add One Student
1. Click **Dashboard** → click **Students** or go to `/students/`
2. Click **Add New Student**
3. Fill in:
   - Name, Father's Name
   - Roll Number (must be unique in the school)
   - Class, Section
   - Date of Birth
   - Gender
   - Mobile number
4. Click **Save**

#### Option B — Bulk Upload via Excel (Recommended for new school)

1. Go to `/students/` → click **Upload Excel Data**
2. Prepare an Excel file (`.xlsx`) with these columns in the first row:

   | Column Header | Example Value |
   |---------------|--------------|
   | name | Ramesh Kumar |
   | father_name | Suresh Kumar |
   | roll_number | 2024001 |
   | class_name | 10 |
   | section | A |
   | dob | 15/08/2010 |
   | gender | M |
   | mobile | 9876543210 |

3. Select the file → click **Upload**
4. Success message will show how many students were added

> **Default Password:** All newly added students (single or bulk upload) get the default password **`1234`**. Students should change this after their first login.

> **File size limit:** Maximum 5 MB per upload.

### 5.2 Edit or Delete a Student
1. Go to `/students/`
2. Search by name or roll number in the search box
3. Click **Edit** on the student row to update details
4. Click **Delete** to remove (cannot be undone)

---

## 6. Test Management

Tests are created by the **District Admin** and are visible **only to students in that district**.

---

### 6.1 Create a Test (District Admin only)

1. Click **Dashboard** (Collector Dashboard)
2. Click **Add Test** button on the dashboard, or go to `/add-test/`
3. Fill in the form:

   | Field | Description |
   |-------|-------------|
   | Test Name | e.g., "Monthly Test October 2025" |
   | Subject Name | e.g., Mathematics, Science |
   | Test Date | Date the test was/will be held |
   | Maximum Marks | Total marks for this test |
   | Question Paper PDF | Upload PDF (optional, max 5 MB) |
   | Answer Key PDF | Upload answer PDF (optional) |

4. Click **Submit**

> The test is automatically linked to your district. Students from other districts will NOT see this test.

> New tests are created as **Inactive** by default — students cannot see them until activated.

---

### 6.2 Activate a Test

Once a test is ready for students to see:

1. Go to Collector Dashboard
2. In the **Tests** table, find the test
3. Click **Activate** button

The test becomes visible to all active students in your district.

### 6.3 Deactivate a Test

To hide a test from students (e.g., after results are declared):

1. Collector Dashboard → Tests table
2. Click **Deactivate** on the test

### 6.4 View Test Results

1. Collector Dashboard → Tests table
2. Click the test name or **View Results** to see student-wise marks
3. Results can be sorted by student name, marks, or percentage

---

## 7. Marks Entry

Marks are entered by **School Admins** for their school's students.

### 7.1 Add Marks for a Student

1. Go to `/marks/` or click **Marks** from your school dashboard
2. Click **Add Marks**
3. Select:
   - **Student** — dropdown shows students in your school
   - **Test** — dropdown shows active tests for your district
   - **Marks** — numeric value (cannot exceed test's maximum marks)
4. Click **Add Marks**

> Each student can have only **one marks entry per test**. If you try to add again, you will get an error — use **Edit** instead.

### 7.2 Edit Marks

1. Go to Marks List → `/marks/`
2. Find the entry
3. Click **Edit** → change the marks → click **Save**

### 7.3 Marks List View

The marks list shows all marks entries for your school, grouped by test. You can:
- Filter by test name
- Sort by student name or marks
- See percentage automatically calculated

---

## 8. Student Portal

Students access a separate portal at `/student-login/`.

### 8.1 Student Login
- Username: **Roll Number**
- Password: **`1234`** (default for all new students)

> Change the default password immediately after first login using the **Change Password** option in the student portal.

### 8.2 My Tests Page (`/student-tests/`)

After login, students see two sections:

**Pending Tests** — active tests from the district that the student has not yet submitted marks for. Shows test name, subject, date, and download links for question paper / answer key.

**Completed Tests** — tests where marks have been entered. Shows:
- Marks obtained
- Percentage
- Date of entry

> Students only see tests from their own district. Tests from other districts are not visible.

### 8.3 Practice Tests (AI-powered)

Students can generate practice questions on any topic:
1. Go to **Practice Test** from student menu
2. Select subject and topic
3. Click **Generate Questions**
4. AI generates MCQ/short answer questions instantly

### 8.4 Student Password Change

Students can change their own password from the student portal settings menu.

---

## 9. Activity Logs (Audit Trail)

**URL:** `/activity-logs/`
**Access:** District Admin only

This page records every important action taken in your district's data.

### What Is Logged

| Action | Example |
|--------|---------|
| LOGIN / LOGOUT | Admin logged in from IP 192.168.1.5 |
| TEST_CREATE | "Monthly Test Oct 2025" created |
| TEST_ACTIVATE / DEACTIVATE | Test activated |
| MARKS_ADD / MARKS_EDIT | Marks added for student Ramesh |
| STUDENT_ADD | New student Priya added |
| SCHOOL_CREATE | New school created |
| REPORT_VIEW | Performance report viewed |

### Filtering Logs

Use the filter bar at the top:
- **Date From / To** — narrow to a date range
- **Action Type** — filter by specific action (LOGIN, MARKS_ADD, etc.)
- **User** — filter by which admin performed the action

Logs are paginated 50 entries per page.

### Why Use It
- Investigate if marks were changed without authorisation
- Check last login time for inactive accounts
- Verify that all schools uploaded student data

---

## 10. Account & Password

### Change Your Password
1. After login, go to `/change-password/`
2. Enter your current password
3. Enter new password (minimum 8 characters, cannot be too common)
4. Confirm new password
5. Click **Change Password**

Password rules:
- Minimum **8 characters**
- Cannot be similar to your username
- Cannot be a commonly used password
- Must be changed every **90 days** (system forces this automatically)

### If Your Account Is Locked
- Wait **30 minutes** — it unlocks automatically
- Or ask your system administrator (the person above you in the hierarchy) to unlock via Django admin

### Forgot Password
Contact your system administrator. There is no self-service password reset — the administrator will reset it from the admin panel.

---

## Quick Reference Card

### District Admin — Top Navbar Links

| Link | Goes To | Purpose |
|------|---------|---------|
| Dashboard | `/collector-dashboard/` | Main analytics |
| Manage Blocks | `/manage/blocks/` | Add / edit blocks |
| Manage Schools | `/manage/schools/` | Add / edit schools |
| Activity Logs | `/activity-logs/` | Audit trail |
| Log Out | — | End session |

### School Admin — Top Navbar Links

| Link | Goes To | Purpose |
|------|---------|---------|
| Dashboard | `/dashboard/` | School summary |
| Students | `/students/` | Add / manage students |
| Marks | `/marks/` | Enter / view marks |
| Log Out | — | End session |

### Key URLs Summary

| URL | Who Uses It |
|-----|------------|
| `/login/` | All admin roles |
| `/student-login/` | Students |
| `/collector-dashboard/` | District Admin |
| `/add-test/` | District Admin |
| `/manage/blocks/create/` | District Admin |
| `/manage/schools/create/` | District / Block Admin |
| `/students/` | School Admin |
| `/upload-student-data/` | School Admin |
| `/marks/` | School Admin |
| `/activity-logs/` | District Admin |
| `/change-password/` | All users |
| `/student-tests/` | Students |

---

## Common Mistakes to Avoid

| Mistake | What Happens | Correct Action |
|---------|-------------|----------------|
| Creating a test without activating it | Students cannot see it | Activate from dashboard after creation |
| Uploading student Excel without correct column headers | Upload fails silently or partial | Match column names exactly as in Section 5.1 |
| Entering marks above maximum marks | Validation error | Check the test's `max_marks` before entry |
| Creating a school under wrong block | School appears in wrong block's data | Contact District Admin to edit school details |
| Sharing login credentials | Security risk, activity log shows wrong user | Each person must have their own account |
| Not logging out on shared computer | Session stays active for 30 minutes | Always click Log Out |

---

*PadhaiWithAI — District User Manual | March 2026*
*For technical support contact your State NIC / System Administrator*
