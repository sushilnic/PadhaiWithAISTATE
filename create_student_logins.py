"""
Student Login Creation Script for PadhaiWithAI
===============================================
Run from project root:
    python manage.py shell < create_student_logins.py

Or run inside Django shell:
    exec(open('create_student_logins.py').read())

Password format: roll_number@123  (e.g., STU001@123)
Students who already have a password are SKIPPED (no overwrite).
"""

import os
import sys
import django

# Setup Django if running standalone
if 'django' not in sys.modules or not hasattr(django, 'apps'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_project.settings')
    django.setup()

from school_app.models import Student, School

# ============================================================
# OPTION 1: Set password for ALL students without a password
# ============================================================
def create_all_student_logins():
    """Set default password for all students who don't have one."""
    students = Student.objects.filter(password__isnull=True) | Student.objects.filter(password='')
    count = 0

    for student in students:
        student.password = f"{student.roll_number}@123"
        student.is_active = True
        student.save(update_fields=['password', 'is_active'])
        count += 1
        print(f"  [OK] {student.roll_number} - {student.name} -> Password: {student.roll_number}@123")

    print(f"\n--- Created logins for {count} students ---")
    return count


# ============================================================
# OPTION 2: Set password for students of a specific school
# ============================================================
def create_logins_for_school(school_name_or_id):
    """Set default password for all students of a specific school."""
    try:
        if isinstance(school_name_or_id, int):
            school = School.objects.get(id=school_name_or_id)
        else:
            school = School.objects.get(name__icontains=school_name_or_id)
    except School.DoesNotExist:
        print(f"School not found: {school_name_or_id}")
        return 0
    except School.MultipleObjectsReturned:
        print(f"Multiple schools match '{school_name_or_id}'. Use school ID instead:")
        for s in School.objects.filter(name__icontains=school_name_or_id):
            print(f"  ID: {s.id} - {s.name}")
        return 0

    students = Student.objects.filter(school=school).filter(
        models_Q(password__isnull=True) | models_Q(password='')
    )
    count = 0

    print(f"\nSchool: {school.name} (ID: {school.id})")
    print("-" * 50)

    for student in students:
        student.password = f"{student.roll_number}@123"
        student.is_active = True
        student.save(update_fields=['password', 'is_active'])
        count += 1
        print(f"  [OK] {student.roll_number} - {student.name}")

    print(f"\n--- Created logins for {count} students in {school.name} ---")
    return count


# ============================================================
# OPTION 3: Create a single student with login
# ============================================================
def create_single_student(name, roll_number, class_name, school_id, password=None):
    """Create a new student with login credentials."""
    try:
        school = School.objects.get(id=school_id)
    except School.DoesNotExist:
        print(f"School ID {school_id} not found.")
        return None

    if Student.objects.filter(roll_number=roll_number).exists():
        print(f"Roll number {roll_number} already exists!")
        return None

    pwd = password or f"{roll_number}@123"

    student = Student.objects.create(
        name=name,
        roll_number=roll_number,
        class_name=str(class_name),
        school=school,
        password=pwd,
        is_active=True
    )

    print(f"  [CREATED] {student.name}")
    print(f"  Roll Number: {student.roll_number}")
    print(f"  Password:    {pwd}")
    print(f"  Class:       {student.class_name}")
    print(f"  School:      {school.name}")
    return student


# ============================================================
# OPTION 4: Bulk create students from a list
# ============================================================
def bulk_create_students(school_id, students_list):
    """
    Bulk create students.

    students_list = [
        {'name': 'Rahul Kumar',  'roll_number': 'STU001', 'class_name': '10'},
        {'name': 'Priya Sharma', 'roll_number': 'STU002', 'class_name': '10'},
    ]
    """
    try:
        school = School.objects.get(id=school_id)
    except School.DoesNotExist:
        print(f"School ID {school_id} not found.")
        return 0

    print(f"\nSchool: {school.name} (ID: {school.id})")
    print("=" * 60)

    created = 0
    skipped = 0

    for s in students_list:
        roll = s['roll_number']
        if Student.objects.filter(roll_number=roll).exists():
            print(f"  [SKIP] {roll} already exists")
            skipped += 1
            continue

        Student.objects.create(
            name=s['name'],
            roll_number=roll,
            class_name=str(s.get('class_name', '10')),
            school=school,
            password=s.get('password', f"{roll}@123"),
            is_active=True
        )
        print(f"  [OK] {roll} - {s['name']} -> Password: {roll}@123")
        created += 1

    print(f"\n--- Created: {created} | Skipped: {skipped} ---")
    return created


# ============================================================
# OPTION 5: Print all students with login status
# ============================================================
def print_login_status():
    """Show all students and whether they have a password set."""
    schools = School.objects.all().order_by('name')

    total = 0
    with_pwd = 0
    without_pwd = 0

    for school in schools:
        students = Student.objects.filter(school=school).order_by('roll_number')
        if not students.exists():
            continue

        print(f"\n{'=' * 60}")
        print(f"School: {school.name} (ID: {school.id})")
        print(f"{'=' * 60}")
        print(f"{'Roll':<15} {'Name':<25} {'Class':<8} {'Password':<10} {'Active'}")
        print(f"{'-'*15} {'-'*25} {'-'*8} {'-'*10} {'-'*6}")

        for s in students:
            has_pwd = 'YES' if s.password else 'NO'
            active = 'YES' if s.is_active else 'NO'
            if s.password:
                with_pwd += 1
            else:
                without_pwd += 1
            total += 1
            print(f"{s.roll_number:<15} {s.name:<25} {s.class_name:<8} {has_pwd:<10} {active}")

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total} students | With password: {with_pwd} | Without: {without_pwd}")
    print(f"{'=' * 60}")


# ============================================================
# Helper import for Q objects
# ============================================================
from django.db.models import Q as models_Q


# ============================================================
# RUN — Uncomment the option you want to use
# ============================================================

if __name__ == '__main__' or True:
    print("\n" + "=" * 60)
    print("   PadhaiWithAI — Student Login Creator")
    print("=" * 60)

    # --- Show current status ---
    print_login_status()

    # --- Create logins for all students without password ---
    print("\n\nSetting passwords for students without login...")
    create_all_student_logins()

    # --- Uncomment below for specific operations ---

    # Create logins for a specific school:
    # create_logins_for_school('Government School Malpura')  # by name
    # create_logins_for_school(1)  # by ID

    # Create a single student:
    # create_single_student(
    #     name='Rahul Kumar',
    #     roll_number='STU001',
    #     class_name='10',
    #     school_id=1,
    #     password='custom_password'  # optional, defaults to roll@123
    # )

    # Bulk create:
    # bulk_create_students(school_id=1, students_list=[
    #     {'name': 'Rahul Kumar',   'roll_number': 'STU001', 'class_name': '10'},
    #     {'name': 'Priya Sharma',  'roll_number': 'STU002', 'class_name': '10'},
    #     {'name': 'Amit Singh',    'roll_number': 'STU003', 'class_name': '9'},
    # ])

    print("\n--- DONE ---")
    print("Students can now login at /student/login/ with:")
    print("  Roll Number: their roll number")
    print("  Password:    roll_number@123")
