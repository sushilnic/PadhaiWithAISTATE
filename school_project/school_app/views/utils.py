"""
Shared utilities, helpers, constants, and all top-level imports for the views package.
"""
from ..text_utils import _strip_think  # noqa: F401  re-exported for views package
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import json
import logging
import os
import time
import urllib.parse

logger = logging.getLogger(__name__)

import pandas as pd

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import (
    Avg, Count, Case, When, F, Q, Sum, Max, Min,
    ExpressionWrapper, FloatField, IntegerField, Value
)
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from django.core.cache import cache
from functools import wraps

from asgiref.sync import async_to_sync

from ..forms import (
    StudentForm, MarksForm, SchoolForm, SchoolAdminRegistrationForm,
    TestForm, LoginForm, ExcelFileUploadForm,
    StateCreateForm, StateEditForm, DistrictCreateForm, DistrictEditForm,
    BlockCreateForm, BlockEditForm, SchoolCreateForm, SchoolEditForm,
)
from ..math_utils import async_solve_math_problem, async_generate_similar_questions
from ..models import (
    School, Student, Marks, Block, Attendance, District, Test, CustomUser, State, PracticeTest,
    ActivityLog, AcademicCalendarEvent,
)
from ..solution_formatter import SolutionFormatter

def rate_limit(max_calls=10, period=60):
    """Cache-based per-user rate limiter. Returns HTTP 429 when exceeded."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                key = f'rl:{view_func.__name__}:{request.user.id}'
                count = cache.get(key, 0)
                if count >= max_calls:
                    logger.warning(
                        'SECURITY: rate limit exceeded user=%s view=%s',
                        request.user.email, view_func.__name__
                    )
                    return HttpResponse(
                        'Too many requests. Please wait a minute and try again.',
                        status=429,
                        content_type='text/plain',
                    )
                cache.set(key, count + 1, period)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Constants for grade category thresholds
CATEGORY_THRESHOLD_33 = 0.33
CATEGORY_THRESHOLD_60 = 0.60
CATEGORY_THRESHOLD_80 = 0.80
CATEGORY_THRESHOLD_90 = 0.90


# ===== Excel upload security helpers =====

EXCEL_MAX_SIZE = 5 * 1024 * 1024   # 5 MB
EXCEL_ALLOWED_EXT = ('.xlsx', '.xls')
EXCEL_XLSX_MAGIC = b'PK\x03\x04'             # ZIP-based (.xlsx, .xlsm)
EXCEL_XLS_MAGIC  = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'  # OLE2 (.xls)
EXCEL_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def validate_excel_upload(uploaded_file):
    """Validate an uploaded Excel file by extension, size, and magic bytes.

    Returns (True, None) on success or (False, error_message) on failure.
    Resets the file pointer to 0 after reading the magic bytes.
    """
    if uploaded_file is None:
        return False, 'No file uploaded.'

    name = (uploaded_file.name or '').lower()
    if not name.endswith(EXCEL_ALLOWED_EXT):
        return False, 'Only Excel files (.xlsx, .xls) are allowed.'

    if uploaded_file.size > EXCEL_MAX_SIZE:
        return False, f'File size exceeds {EXCEL_MAX_SIZE // (1024*1024)} MB limit.'

    # Read first 8 bytes to verify file content matches the extension
    try:
        header = uploaded_file.read(8)
        uploaded_file.seek(0)
    except Exception:
        return False, 'Could not read uploaded file.'

    if name.endswith('.xlsx'):
        if not header.startswith(EXCEL_XLSX_MAGIC):
            return False, 'File is not a valid .xlsx file (content mismatch).'
    elif name.endswith('.xls'):
        if not header.startswith(EXCEL_XLS_MAGIC):
            return False, 'File is not a valid .xls file (content mismatch).'

    return True, None


def sanitize_cell(value):
    """Strip leading formula-injection characters from a cell value.

    Excel/CSV cells starting with =, +, -, @ are interpreted as formulas
    when the file is re-opened. Prefix such values with a single quote.
    """
    if value is None:
        return value
    s = str(value)
    if s and s[0] in EXCEL_FORMULA_PREFIXES:
        return "'" + s
    return s


# ===== Login brute-force protection (per IP) =====
# Per-account lockout doesn't help when an attacker rotates through many usernames
# trying the same default password (e.g. "1234"). Per-IP counter caps the total
# failed attempts from one source regardless of which account they target.

LOGIN_IP_MAX_FAILS = 20          # over the window below
LOGIN_IP_WINDOW    = 600         # 10 minutes
LOGIN_IP_LOCK_MINS = 30          # block duration after hitting the limit


def _ip_login_key(ip, kind='login'):
    return f'iprl:{kind}:{ip}'


def login_ip_blocked(request, kind='login'):
    """Return (blocked: bool, retry_after_minutes: int)."""
    ip = get_client_ip(request) or 'unknown'
    block_key = _ip_login_key(ip, kind=f'{kind}_block')
    until = cache.get(block_key)
    if until and until > time.time():
        return True, max(1, int((until - time.time()) // 60) + 1)
    return False, 0


def login_ip_register_failure(request, kind='login'):
    """Increment failure counter for this IP; lock the IP if threshold exceeded.
    Returns True if this attempt put the IP into the locked state.
    """
    ip = get_client_ip(request) or 'unknown'
    counter_key = _ip_login_key(ip, kind=f'{kind}_count')
    fails = cache.get(counter_key, 0) + 1
    cache.set(counter_key, fails, LOGIN_IP_WINDOW)
    if fails >= LOGIN_IP_MAX_FAILS:
        cache.set(
            _ip_login_key(ip, kind=f'{kind}_block'),
            time.time() + LOGIN_IP_LOCK_MINS * 60,
            LOGIN_IP_LOCK_MINS * 60,
        )
        logger.warning('SECURITY: IP %s blocked from %s after %d failed attempts', ip, kind, fails)
        return True
    return False


def login_ip_reset(request, kind='login'):
    """Clear counters on successful login so legit users aren't penalised."""
    ip = get_client_ip(request) or 'unknown'
    cache.delete(_ip_login_key(ip, kind=f'{kind}_count'))
    cache.delete(_ip_login_key(ip, kind=f'{kind}_block'))


# ===== Image upload security helpers =====
# Cap pixel count to defeat "decompression bombs": a tiny PNG that expands to
# gigabytes when decoded. Pillow's default MAX_IMAGE_PIXELS is ~178 megapixels,
# which is still enough to OOM small servers. 25 MP is plenty for educational
# uploads (handles photos up to 5184×4860).
IMAGE_MAX_PIXELS = 25_000_000


def open_image_safely(raw_bytes, mode='RGB'):
    """Safely decode user-uploaded image bytes.

    - Caps pixels via Pillow's MAX_IMAGE_PIXELS to prevent decompression bombs.
    - Calls verify() first to catch malformed files cheaply.
    - Returns a decoded PIL Image, or raises ValueError on any failure.

    Caller is responsible for size-limit (e.g. 5 MB) before calling.
    """
    from PIL import Image, UnidentifiedImageError
    import io

    # Apply pixel cap (process-wide setting, but safe to set per-call)
    Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS

    try:
        # First pass: verify header only (cheap, doesn't decode pixels)
        probe = Image.open(io.BytesIO(raw_bytes))
        probe.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('Image is too large (decompression bomb).')
    except (UnidentifiedImageError, Exception):
        raise ValueError('Could not read image.')

    try:
        # Second pass: actually decode (verify closes the file)
        img = Image.open(io.BytesIO(raw_bytes)).convert(mode)
        return img
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('Image is too large (decompression bomb).')
    except Exception:
        raise ValueError('Could not decode image.')

# Sarvam AI configuration
try:
    from sarvamai import SarvamAI
    from sarvamai.core.api_error import ApiError
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
except ImportError:
    SarvamAI = None
    ApiError = Exception
    SARVAM_API_KEY = None


# ===== Activity Log Helpers =====

def get_client_ip(request):
    """Return the client IP address.
    Uses REMOTE_ADDR (the trusted network peer) to prevent X-Forwarded-For spoofing.
    """
    return request.META.get('REMOTE_ADDR', '')


def _get_user_role(user):
    """Return a human-readable role string for a CustomUser."""
    if user.is_system_admin:
        return 'System Admin'
    if user.is_state_user:
        return 'State'
    if user.is_district_user:
        return 'District'
    if user.is_block_user:
        return 'Block'
    if user.is_school_user:
        return 'School'
    return 'Unknown'


def resolve_district(user=None, student=None):
    """Walk the hierarchy to find the district for a user or student."""
    try:
        if student:
            return student.school.block.district
        if user:
            if user.is_district_user:
                return District.objects.filter(admin=user).first()
            if user.is_block_user:
                block = Block.objects.filter(admin=user).first()
                return block.district if block else None
            if user.is_school_user:
                school = School.objects.filter(admin=user).first()
                return school.block.district if school and school.block else None
    except Exception:
        pass
    return None


def log_activity(request, action_type, description, user=None, student=None, district=None):
    """Create an ActivityLog record. Never raises — logging must not break main flow."""
    try:
        log_user = user or (request.user if hasattr(request, 'user') and request.user.is_authenticated else None)
        log_student = student

        if log_user:
            email = log_user.email
            role = _get_user_role(log_user)
        elif log_student:
            email = f"student:{log_student.roll_number}"
            role = 'Student'
        else:
            email = ''
            role = ''

        if district is None:
            district = resolve_district(user=log_user, student=log_student)

        ActivityLog.objects.create(
            user=log_user,
            student=log_student,
            user_email=email,
            user_role=role,
            action_type=action_type,
            description=description,
            district=district,
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass


def login_or_student_required(view_func):
    """Decorator to allow access for Django auth users OR student session login."""
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated via Django auth OR student session
        is_django_user = request.user.is_authenticated
        is_student = request.session.get('is_student', False)

        if is_django_user or is_student:
            return view_func(request, *args, **kwargs)

        # Redirect to login page
        messages.error(request, 'Please login to access this page.')
        return redirect('login')
    return wrapper


@login_required
def get_active_users_count():
    sessions = Session.objects.filter(expire_date__gte=timezone.now())

    active_users_count = 0

    for session in sessions:
        session_data = session.get_decoded()

        if 'user_id' in session_data:
            user_id = session_data['user_id']
            try:
                User.objects.get(id=user_id)
                active_users_count += 1
            except User.DoesNotExist:
                continue

    return active_users_count


def _get_user_district(request):
    """Return the District for the logged-in user (district / block / school)."""
    user = request.user
    if user.is_district_user:
        try:
            return District.objects.get(admin=user)
        except District.DoesNotExist:
            return None
    if user.is_block_user:
        try:
            return Block.objects.get(admin=user).district
        except Block.DoesNotExist:
            return None
    # School user
    try:
        return School.objects.get(admin=user).block.district
    except School.DoesNotExist:
        return None


def _events_as_json(district):
    """Return calendar events for a district as a JSON-serialisable list."""
    events = AcademicCalendarEvent.objects.filter(district=district)
    color_map = {
        'teaching': '#1e3c72',
        'exam':     '#dc2626',
        'holiday':  '#059669',
        'meeting':  '#d97706',
        'other':    '#6d28d9',
    }
    result = []
    for e in events:
        result.append({
            'start': str(e.start_date),
            'end':   str(e.end_date),
            'title': e.title,
            'type':  e.event_type,
            'color': color_map.get(e.event_type, '#1e3c72'),
            'id':    e.id,
        })
    return result


def _generate_math_captcha(request):
    """Generate a simple math captcha and store answer in session."""
    import random
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    request.session['captcha_answer'] = a + b
    return f"{a} + {b}"
