"""
Models module for PadhaiWithAI school management application.
Contains all Django model definitions for the database schema.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings


class CustomUserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with the given email and password."""
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.is_district_user = False
        user.is_block_user = False
        user.is_school_user = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_system_admin', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom user model with email as the primary identifier.
    Supports multiple user roles: system_admin, district_user, block_user, school_user.
    """
    email = models.EmailField(unique=True)
    is_system_admin = models.BooleanField(default=False)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)

    # Override groups and user_permissions to avoid reverse accessor conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to.',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.',
    )

    # Role flags (hierarchy: State > District > Block > School)
    is_state_user = models.BooleanField(default=False)
    is_district_user = models.BooleanField(default=False)
    is_block_user = models.BooleanField(default=False)
    is_school_user = models.BooleanField(default=True)

    # Security fields
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    current_session_key = models.CharField(max_length=40, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_school_user']),
        ]

    def __str__(self):
        return self.email


class State(models.Model):
    """Represents a state in the education hierarchy."""
    name_english = models.CharField(max_length=100)
    name_hindi = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True, help_text="State code (e.g., RJ for Rajasthan)")
    admin = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='state_admin'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'State'
        verbose_name_plural = 'States'
        ordering = ['name_english']

    def __str__(self):
        return self.name_english


class District(models.Model):
    """Represents an educational district within a state."""
    name_english = models.CharField(max_length=100)
    name_hindi = models.CharField(max_length=100)
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name='districts',
        null=True,
        blank=True
    )
    admin = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='district_admin'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = 'District'
        verbose_name_plural = 'Districts'
        ordering = ['name_english']
        indexes = [
            models.Index(fields=['state']),
        ]

    def __str__(self):
        return self.name_english


class Block(models.Model):
    """Represents an administrative block within a district."""
    name_english = models.CharField(max_length=100)
    name_hindi = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='blocks')
    admin = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='block_admin',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = 'Block'
        verbose_name_plural = 'Blocks'
        ordering = ['name_english']
        indexes = [
            models.Index(fields=['district']),
        ]

    def __str__(self):
        return self.name_english


class School(models.Model):
    """Represents a school entity."""
    name = models.CharField(max_length=100)
    admin = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='administered_school'
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='created_schools',
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name='block_schools'
    )
    nic_code = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        ordering = ['name']
        indexes = [
            models.Index(fields=['block']),
            models.Index(fields=['admin']),
        ]

    def __str__(self):
        return self.name


class Student(models.Model):
    """Represents a student enrolled in a school."""
    CLASS_CHOICES = [
        ('1', 'Class 1'),
        ('2', 'Class 2'),
        ('3', 'Class 3'),
        ('4', 'Class 4'),
        ('5', 'Class 5'),
        ('6', 'Class 6'),
        ('7', 'Class 7'),
        ('8', 'Class 8'),
        ('9', 'Class 9'),
        ('10', 'Class 10'),
        ('11', 'Class 11'),
        ('12', 'Class 12'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20, unique=True)
    class_name = models.CharField(
        max_length=2,
        choices=CLASS_CHOICES,
        verbose_name='Class'
    )
    # Student login credentials
    password = models.CharField(max_length=128, null=True, blank=True, help_text="Student login password")
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['roll_number']
        indexes = [
            models.Index(fields=['school']),
            models.Index(fields=['roll_number']),
            models.Index(fields=['class_name']),
        ]

    def __str__(self):
        return self.name


class Book(models.Model):
    """Represents a curriculum book with content stored in JSON."""
    name = models.CharField(max_length=100)
    language = models.CharField(max_length=20)
    json_file_path = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Book'
        verbose_name_plural = 'Books'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.language})"


class Test(models.Model):
    """Represents a test/exam paper."""
    test_number = models.AutoField(primary_key=True)
    test_name = models.CharField(max_length=255)
    subject_name = models.CharField(max_length=255)
    pdf_file_questions = models.FileField(
        upload_to='test_pdfs/questions/',
        null=True,
        blank=True
    )
    pdf_file_answers = models.FileField(
        upload_to='test_pdfs/answers/',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=False)
    test_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    max_marks = models.FloatField()
    district = models.ForeignKey(
        'District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tests'
    )

    class Meta:
        verbose_name = 'Test'
        verbose_name_plural = 'Tests'
        ordering = ['-test_number']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['test_date']),
        ]

    def __str__(self):
        return self.test_name


class Marks(models.Model):
    """Records student marks for a specific test."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks_records')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='marks')
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mark'
        verbose_name_plural = 'Marks'
        unique_together = ('student', 'test')
        indexes = [
            models.Index(fields=['student', 'test']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.test.test_name}: {self.marks}"

    @property
    def percentage(self):
        """Calculate the percentage score for this mark."""
        if self.test.max_marks > 0:
            return (float(self.marks) / float(self.test.max_marks)) * 100
        return 0


class AcademicCalendarEvent(models.Model):
    """District-wise academic calendar events."""
    EVENT_TYPES = [
        ('teaching',  'Teaching / Syllabus'),
        ('exam',      'Exam / Assessment'),
        ('holiday',   'Holiday'),
        ('meeting',   'Meeting'),
        ('other',     'Other'),
    ]
    district    = models.ForeignKey('District', on_delete=models.CASCADE, related_name='calendar_events')
    title       = models.CharField(max_length=300)
    start_date  = models.DateField()
    end_date    = models.DateField()
    event_type  = models.CharField(max_length=20, choices=EVENT_TYPES, default='teaching')
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return f"{self.district} | {self.title} ({self.start_date})"


class Attendance(models.Model):
    """Tracks daily attendance for students."""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField(auto_now_add=True)
    is_present = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        unique_together = ('student', 'date')
        indexes = [
            models.Index(fields=['student', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        status = 'Present' if self.is_present else 'Absent'
        return f"{self.student.name} - {self.date}: {status}"


class PracticeTest(models.Model):
    """Records student practice test attempts and progress."""
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='practice_tests')
    topic = models.CharField(max_length=200)  # Chapter name from book
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    total_questions = models.IntegerField(default=10)
    correct_answers = models.IntegerField(default=0)
    wrong_answers = models.IntegerField(default=0)
    time_taken = models.IntegerField(help_text="Time in seconds", null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Practice Test'
        verbose_name_plural = 'Practice Tests'
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['student', 'topic']),
            models.Index(fields=['attempted_at']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.topic}: {self.correct_answers}/{self.total_questions}"

    @property
    def score_percentage(self):
        if self.total_questions > 0:
            return round((self.correct_answers / self.total_questions) * 100, 1)
        return 0


class ActivityLog(models.Model):
    """Records user activity for security audit trail."""
    ACTION_TYPES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('STUDENT_LOGIN', 'Student Login'),
        ('STUDENT_LOGOUT', 'Student Logout'),
        ('CREATE', 'Create'),
        ('EDIT', 'Edit'),
        ('DELETE', 'Delete'),
        ('TOGGLE', 'Toggle'),
        ('MARKS_ENTRY', 'Marks Entry'),
        ('ATTENDANCE', 'Attendance'),
        ('TEST_CREATE', 'Test Create'),
        ('TEST_ACTIVATE', 'Test Activate'),
        ('TEST_DEACTIVATE', 'Test Deactivate'),
        ('VIDEO_LEARNING', 'Video Learning'),
        ('PRACTICE_TEST', 'Practice Test'),
        ('UPLOAD', 'Upload'),
        ('PASSWORD_CHANGE', 'Password Change'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    user_email = models.CharField(max_length=255, blank=True, default='')
    user_role = models.CharField(max_length=50, blank=True, default='')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField(blank=True, default='')
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['district', '-timestamp']),
            models.Index(fields=['action_type']),
        ]

    def __str__(self):
        return f"{self.timestamp} | {self.action_type} | {self.user_email}"
