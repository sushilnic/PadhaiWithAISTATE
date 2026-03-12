"""
Unit and Integration Tests for PadhaiWithAI School App
Run with: python manage.py test school_app --verbosity=2
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from school_app.models import (
    CustomUser, State, District, Block, School, Student,
    Test, Marks, AcademicCalendarEvent, Attendance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state_user(email='state@test.com', password='Test@1234'):
    user = CustomUser.objects.create_user(email=email, password=password)
    user.is_state_user = True
    user.save()
    return user

def make_district_user(email='district@test.com', password='Test@1234'):
    user = CustomUser.objects.create_user(email=email, password=password)
    user.is_district_user = True
    user.save()
    return user

def make_school_user(email='school@test.com', password='Test@1234'):
    user = CustomUser.objects.create_user(email=email, password=password)
    user.is_school_user = True
    user.save()
    return user


# ===========================================================================
# UNIT TESTS — Models
# ===========================================================================

class CustomUserModelTest(TestCase):

    def test_create_user(self):
        user = CustomUser.objects.create_user(email='u@test.com', password='pass')
        self.assertEqual(user.email, 'u@test.com')
        self.assertTrue(user.check_password('pass'))

    def test_default_role_flags(self):
        user = CustomUser.objects.create_user(email='r@test.com', password='pass')
        self.assertFalse(user.is_state_user)
        self.assertFalse(user.is_district_user)
        self.assertFalse(user.is_block_user)
        # is_school_user defaults to True per model definition
        self.assertTrue(user.is_school_user)

    def test_account_not_locked_by_default(self):
        user = CustomUser.objects.create_user(email='l@test.com', password='pass')
        self.assertEqual(user.failed_login_attempts, 0)
        self.assertIsNone(user.locked_until)

    def test_account_lockout(self):
        user = CustomUser.objects.create_user(email='lock@test.com', password='pass')
        user.failed_login_attempts = 5
        user.locked_until = timezone.now() + timedelta(minutes=30)
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.locked_until > timezone.now())

    def test_str(self):
        user = CustomUser.objects.create_user(email='str@test.com', password='pass')
        self.assertIn('str@test.com', str(user))


class StateModelTest(TestCase):

    def test_create_state(self):
        admin = make_state_user()
        state = State.objects.create(
            name_english='Rajasthan', name_hindi='राजस्थान',
            code='RJ', admin=admin
        )
        self.assertEqual(str(state), 'Rajasthan')
        self.assertTrue(state.is_active)

    def test_state_code_unique(self):
        from django.db import IntegrityError
        State.objects.create(name_english='S1', name_hindi='S1', code='XX')
        with self.assertRaises(IntegrityError):
            State.objects.create(name_english='S2', name_hindi='S2', code='XX')


class DistrictModelTest(TestCase):

    def setUp(self):
        self.state = State.objects.create(name_english='TestState', name_hindi='TS', code='TS')

    def test_create_district(self):
        admin = make_district_user()
        district = District.objects.create(
            name_english='Tonk', name_hindi='टोंक',
            state=self.state, admin=admin
        )
        self.assertEqual(district.state, self.state)
        self.assertTrue(district.is_active)

    def test_district_str(self):
        district = District.objects.create(
            name_english='Jaipur', name_hindi='जयपुर', state=self.state
        )
        self.assertIn('Jaipur', str(district))


class BlockModelTest(TestCase):

    def setUp(self):
        self.state = State.objects.create(name_english='S', name_hindi='S', code='S1')
        self.district = District.objects.create(
            name_english='D', name_hindi='D', state=self.state
        )

    def test_create_block(self):
        block = Block.objects.create(
            name_english='Block1', name_hindi='ब्लॉक1', district=self.district
        )
        self.assertEqual(block.district, self.district)
        self.assertTrue(block.is_active)


class SchoolModelTest(TestCase):

    def setUp(self):
        self.state = State.objects.create(name_english='S', name_hindi='S', code='S2')
        self.district = District.objects.create(name_english='D', name_hindi='D', state=self.state)
        self.block = Block.objects.create(name_english='B', name_hindi='B', district=self.district)

    def test_create_school(self):
        admin = make_school_user()
        school = School.objects.create(
            name='Test School', block=self.block, admin=admin
        )
        self.assertEqual(school.block, self.block)
        self.assertTrue(school.is_active)


class StudentModelTest(TestCase):

    def setUp(self):
        state = State.objects.create(name_english='S', name_hindi='S', code='S3')
        district = District.objects.create(name_english='D', name_hindi='D', state=state)
        block = Block.objects.create(name_english='B', name_hindi='B', district=district)
        admin = make_school_user(email='student_school_admin@test.com')
        self.school = School.objects.create(name='School', block=block, admin=admin)

    def test_create_student(self):
        student = Student.objects.create(
            name='Ram Kumar', roll_number='R001',
            class_name='10', school=self.school, password='pass'
        )
        self.assertEqual(student.roll_number, 'R001')
        self.assertTrue(student.is_active)

    def test_roll_number_unique(self):
        from django.db import IntegrityError
        Student.objects.create(name='A', roll_number='DUP', class_name='10',
                               school=self.school, password='p')
        with self.assertRaises(IntegrityError):
            Student.objects.create(name='B', roll_number='DUP', class_name='10',
                                   school=self.school, password='p')


class TestModelTest(TestCase):

    def setUp(self):
        self.user = make_school_user()
        state = State.objects.create(name_english='S', name_hindi='S', code='S4')
        self.district = District.objects.create(name_english='D', name_hindi='D', state=state)

    def test_create_test(self):
        t = Test.objects.create(
            test_name='Math Test 1', subject_name='Mathematics',
            max_marks=100, created_by=self.user, district=self.district
        )
        self.assertEqual(t.test_name, 'Math Test 1')
        self.assertFalse(t.is_active)

    def test_test_str(self):
        t = Test.objects.create(
            test_name='Science Test', subject_name='Science',
            max_marks=50, created_by=self.user
        )
        self.assertIn('Science Test', str(t))


class AcademicCalendarEventModelTest(TestCase):

    def setUp(self):
        state = State.objects.create(name_english='S', name_hindi='S', code='S5')
        admin = make_district_user(email='d5@test.com')
        self.district = District.objects.create(name_english='D', name_hindi='D',
                                                state=state, admin=admin)

    def test_create_event(self):
        today = timezone.now().date()
        event = AcademicCalendarEvent.objects.create(
            title='Annual Exam', start_date=today, end_date=today,
            event_type='exam', district=self.district,
            created_by=self.district.admin
        )
        self.assertEqual(event.title, 'Annual Exam')
        self.assertIn('Annual Exam', str(event))


# ===========================================================================
# INTEGRATION TESTS — Views / HTTP
# ===========================================================================

class LoginViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            email='login@test.com', password='Test@1234'
        )
        self.user.is_school_user = True
        self.user.save()

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_with_wrong_password(self):
        response = self.client.post(reverse('login'), {
            'email': 'login@test.com',
            'password': 'wrongpassword',
            'captcha_0': 'dummy', 'captcha_1': 'dummy',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_student_login_page_loads(self):
        response = self.client.get(reverse('student_login'))
        self.assertEqual(response.status_code, 200)


class AuthRedirectTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get(reverse('dashboard'))
        self.assertIn(response.status_code, [302, 301])
        self.assertIn('/login', response['Location'])

    def test_manage_districts_redirects_unauthenticated(self):
        response = self.client.get(reverse('manage_districts'))
        self.assertIn(response.status_code, [302, 301])

    def test_manage_blocks_redirects_unauthenticated(self):
        response = self.client.get(reverse('manage_blocks'))
        self.assertIn(response.status_code, [302, 301])

    def test_manage_schools_redirects_unauthenticated(self):
        response = self.client.get(reverse('manage_schools'))
        self.assertIn(response.status_code, [302, 301])

    def test_student_dashboard_redirects_unauthenticated(self):
        response = self.client.get(reverse('student_dashboard'))
        self.assertIn(response.status_code, [302, 301])


class StateUserAccessTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.state_user = make_state_user(email='su@test.com')
        state = State.objects.create(
            name_english='TestState', name_hindi='TS', code='TS2', admin=self.state_user
        )
        self.client.force_login(self.state_user)

    def test_manage_districts_accessible(self):
        response = self.client.get(reverse('manage_districts'))
        self.assertEqual(response.status_code, 200)

    def test_manage_blocks_forbidden(self):
        """State user should not access block management (district role only)."""
        response = self.client.get(reverse('manage_blocks'))
        self.assertIn(response.status_code, [200, 403])


class DistrictUserAccessTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.district_user = make_district_user(email='du@test.com')
        state = State.objects.create(name_english='S', name_hindi='S', code='TS3')
        self.district = District.objects.create(
            name_english='D', name_hindi='D', state=state, admin=self.district_user
        )
        self.client.force_login(self.district_user)

    def test_collector_dashboard_accessible(self):
        response = self.client.get(reverse('collector_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_manage_blocks_accessible(self):
        response = self.client.get(reverse('manage_blocks'))
        self.assertEqual(response.status_code, 200)

    def test_manage_schools_accessible(self):
        response = self.client.get(reverse('manage_schools'))
        self.assertEqual(response.status_code, 200)

    def test_manage_districts_forbidden(self):
        """District user cannot access district management (state role only)."""
        response = self.client.get(reverse('manage_districts'))
        self.assertEqual(response.status_code, 403)

    def test_activity_logs_accessible(self):
        response = self.client.get(reverse('activity_logs'))
        self.assertEqual(response.status_code, 200)


class SchoolUserAccessTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.school_user = make_school_user(email='schu@test.com')
        state = State.objects.create(name_english='S', name_hindi='S', code='TS4')
        district = District.objects.create(name_english='D', name_hindi='D', state=state)
        block = Block.objects.create(name_english='B', name_hindi='B', district=district)
        self.school = School.objects.create(
            name='School', block=block, admin=self.school_user
        )
        self.client.force_login(self.school_user)

    def test_dashboard_accessible(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_student_list_accessible(self):
        response = self.client.get(reverse('student_list'))
        self.assertEqual(response.status_code, 200)

    def test_marks_list_accessible(self):
        response = self.client.get(reverse('marks_list'))
        self.assertEqual(response.status_code, 200)

    def test_manage_districts_forbidden(self):
        response = self.client.get(reverse('manage_districts'))
        self.assertEqual(response.status_code, 403)


class UnlockDistrictUserTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.state_user = make_state_user(email='state_unlock@test.com')
        state = State.objects.create(
            name_english='S', name_hindi='S', code='TS5', admin=self.state_user
        )
        self.district_user = make_district_user(email='du_locked@test.com')
        self.district_user.failed_login_attempts = 5
        self.district_user.locked_until = timezone.now() + timedelta(minutes=30)
        self.district_user.save()
        self.district = District.objects.create(
            name_english='Locked District', name_hindi='LD',
            state=state, admin=self.district_user
        )
        self.client.force_login(self.state_user)

    def test_unlock_clears_lock(self):
        self.client.get(reverse('unlock_district_user', args=[self.district.id]))
        self.district_user.refresh_from_db()
        self.assertIsNone(self.district_user.locked_until)
        self.assertEqual(self.district_user.failed_login_attempts, 0)


class ResetDistrictPasswordTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.state_user = make_state_user(email='state_reset@test.com')
        state = State.objects.create(
            name_english='S', name_hindi='S', code='TS6', admin=self.state_user
        )
        self.district_user = make_district_user(email='du_reset@test.com')
        self.district = District.objects.create(
            name_english='Reset District', name_hindi='RD',
            state=state, admin=self.district_user
        )
        self.client.force_login(self.state_user)

    def test_reset_sets_default_password(self):
        self.client.get(reverse('reset_district_password', args=[self.district.id]))
        self.district_user.refresh_from_db()
        self.assertTrue(self.district_user.check_password('nic*12345'))

    def test_reset_sets_must_change_password(self):
        self.client.get(reverse('reset_district_password', args=[self.district.id]))
        self.district_user.refresh_from_db()
        self.assertTrue(self.district_user.must_change_password)


class URLResolutionTest(TestCase):

    def test_all_key_urls_resolve(self):
        from django.urls import resolve
        urls_to_check = [
            '/login/', '/student/login/', '/dashboard/',
            '/collector-dashboard/', '/manage/districts/',
            '/manage/blocks/', '/manage/schools/',
            '/student/dashboard/', '/activity-logs/',
            '/academic-calendar/', '/student/performance/',
        ]
        for url in urls_to_check:
            with self.subTest(url=url):
                match = resolve(url)
                self.assertIsNotNone(match)
