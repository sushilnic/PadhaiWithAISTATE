"""
Authentication views: login, logout, password change, student auth.
"""
from .utils import *
from .utils import _strip_think, _generate_math_captcha
from .hierarchy import get_user_hierarchy


def is_system_admin(user):
    return user.is_authenticated and user.is_system_admin

def _login_context(form):
    """Shared context for every login_view render — always includes current toppers."""
    from .topper import get_current_toppers
    return {'form': form, 'toppers': get_current_toppers(limit=20)}


def login_view(request):
    if request.method == 'POST':
        # IP-level brute-force guard (defeats email-rotation attacks)
        blocked, retry_mins = login_ip_blocked(request, kind='admin_login')
        if blocked:
            form = LoginForm()
            messages.error(request, f'Too many failed attempts from this network. Try again in {retry_mins} minutes.')
            return render(request, 'school_app/login.html', _login_context(form))

        form = LoginForm(request.POST)
        if form.is_valid():
            # `identifier` can be either an email address or a username —
            # our EmailOrUsernameBackend figures out which and does an
            # iexact match on either field.
            identifier = form.cleaned_data['identifier']
            password   = form.cleaned_data['password']

            # Check account lockout — look up by email OR username so a user
            # trying to log in with their username also hits their lockout
            # record (previously only email lookups triggered the lockout).
            from django.db.models import Q
            target_user = (CustomUser.objects
                           .filter(Q(email__iexact=identifier) | Q(username__iexact=identifier))
                           .first())
            if target_user:
                if target_user.locked_until and target_user.locked_until > timezone.now():
                    remaining = int((target_user.locked_until - timezone.now()).total_seconds() // 60) + 1
                    log_activity(request, 'LOGIN', f'Login blocked (account locked): {identifier}')
                    messages.error(request, f'Account locked. Try again in {remaining} minutes.')
                    return render(request, 'school_app/login.html', _login_context(form))
                # Clear expired lock
                if target_user.locked_until and target_user.locked_until <= timezone.now():
                    target_user.locked_until = None
                    target_user.failed_login_attempts = 0
                    target_user.save(update_fields=['locked_until', 'failed_login_attempts'])

            # Custom backend accepts the value under either kwarg.
            user = authenticate(request, username=identifier, password=password)
            if user is not None:
                # Reset per-account and per-IP failure counters
                user.failed_login_attempts = 0
                user.locked_until = None
                login_ip_reset(request, kind='admin_login')
                # Concurrent session control: invalidate old session
                if user.current_session_key:
                    try:
                        Session.objects.filter(session_key=user.current_session_key).delete()
                    except Exception:
                        pass
                login(request, user)
                # Store new session key
                user.current_session_key = request.session.session_key
                user.save(update_fields=['failed_login_attempts', 'locked_until', 'current_session_key'])
                log_activity(request, 'LOGIN', f'User logged in: {user.email}')
                # Redirect based on user role (hierarchy order: State > District > Block > School)
                if user.is_system_admin:
                    return redirect('system_admin_dashboard')
                elif user.is_state_user:
                    return redirect('state_dashboard')
                elif user.is_district_user or user.groups.filter(name='Collector').exists():
                    return redirect('collector_dashboard')
                elif user.is_block_user:
                    return redirect('block_dashboard')
                elif School.objects.filter(admin=user).exists():
                    return redirect('dashboard')
                else:
                    return redirect('school_add')
            else:
                # Failed login — increment per-IP counter (works even when email doesn't exist)
                login_ip_register_failure(request, kind='admin_login')
                log_activity(request, 'LOGIN', f'Failed login attempt: {identifier}')
                if target_user:
                    from django.conf import settings as django_settings
                    max_attempts = getattr(django_settings, 'ACCOUNT_LOCKOUT_ATTEMPTS', 5)
                    lockout_mins = getattr(django_settings, 'ACCOUNT_LOCKOUT_DURATION', 30)
                    target_user.failed_login_attempts += 1
                    if target_user.failed_login_attempts >= max_attempts:
                        target_user.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_mins)
                        target_user.save(update_fields=['failed_login_attempts', 'locked_until'])
                        log_activity(request, 'LOGIN', f'Account locked after {max_attempts} failed attempts: {identifier}')
                        messages.error(request, f'Account locked for {lockout_mins} minutes due to too many failed attempts.')
                        return render(request, 'school_app/login.html', _login_context(form))
                    target_user.save(update_fields=['failed_login_attempts'])
                messages.error(request, 'Invalid credentials')
    else:
        form = LoginForm()
    return render(request, 'school_app/login.html', _login_context(form))


@require_http_methods(["POST"])
def logout_view(request):
    """Admin logout — invalidates all tracked sessions for this user."""
    if request.user.is_authenticated:
        log_activity(request, 'LOGOUT', f'User logged out: {request.user.email}')
        user = request.user
        # Invalidate the tracked session (defeats hijacked parallel sessions)
        if user.current_session_key:
            try:
                Session.objects.filter(session_key=user.current_session_key).delete()
            except Exception:
                logger.exception('logout_view: failed to delete tracked session')
        # Also delete current session in case it differs from the tracked one
        current_key = request.session.session_key
        if current_key and current_key != user.current_session_key:
            try:
                Session.objects.filter(session_key=current_key).delete()
            except Exception:
                pass
        user.current_session_key = None
        user.save(update_fields=['current_session_key'])
    logout(request)
    return redirect('login')


@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)  # Important: Keeps the user logged in after password change
            # Update security fields
            request.user.password_changed_at = timezone.now()
            request.user.must_change_password = False
            request.user.save(update_fields=['password_changed_at', 'must_change_password'])
            log_activity(request, 'PASSWORD_CHANGE', f'Password changed: {request.user.email}')
            messages.success(request, 'Your password was successfully updated!')
            return redirect('change_password')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'school_app/auth/change_password.html', {'form': form})


def student_login(request):
    """Handle student login using roll number and password."""
    if request.method == 'POST':
        # IP-level brute-force guard (defeats roll-number rotation attacks)
        blocked, retry_mins = login_ip_blocked(request, kind='student_login')
        if blocked:
            captcha_question = _generate_math_captcha(request)
            messages.error(request, f'Too many failed attempts from this network. Try again in {retry_mins} minutes.')
            return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

        roll_number = request.POST.get('roll_number', '').strip()
        password = request.POST.get('password', '').strip()
        captcha_input = request.POST.get('captcha', '').strip()

        # Validate captcha — pop removes the old answer so it cannot be reused
        expected = request.session.pop('captcha_answer', None)
        request.session.modified = True   # force save so the pop is persisted
        captcha_question = _generate_math_captcha(request)  # fresh question for next attempt

        if not captcha_input or expected is None:
            login_ip_register_failure(request, kind='student_login')
            messages.error(request, 'Please solve the math question.')
            return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

        try:
            if int(captcha_input) != int(expected):
                login_ip_register_failure(request, kind='student_login')
                messages.error(request, 'Wrong answer to the math question. Please try again.')
                return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})
        except (ValueError, TypeError):
            login_ip_register_failure(request, kind='student_login')
            messages.error(request, 'Please enter a valid number for the math question.')
            return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

        if not roll_number or not password:
            login_ip_register_failure(request, kind='student_login')
            messages.error(request, 'Please enter both roll number and password.')
            return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

        try:
            student = Student.objects.select_related('school').get(roll_number=roll_number)

            if not student.is_active:
                messages.error(request, 'Your account has been deactivated. Please contact your school.')
                return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

            # Check account lockout
            if student.locked_until and student.locked_until > timezone.now():
                remaining = int((student.locked_until - timezone.now()).total_seconds() // 60) + 1
                log_activity(request, 'STUDENT_LOGIN', f'Student login blocked (locked): {roll_number}', student=student)
                messages.error(request, f'Account locked. Try again in {remaining} minutes.')
                return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})
            # Clear expired lock
            if student.locked_until and student.locked_until <= timezone.now():
                student.locked_until = None
                student.failed_login_attempts = 0
                student.save(update_fields=['locked_until', 'failed_login_attempts'])

            # Check password (hashed comparison)
            password_valid = False
            if student.password:
                if student.password.startswith(('pbkdf2_sha256$', 'bcrypt', 'argon2')):
                    # Already hashed — use check_password
                    password_valid = check_password(password, student.password)
                else:
                    # Legacy plain text — compare directly, then auto-hash
                    if student.password == password:
                        password_valid = True
                        student.password = make_password(password)
                        student.save(update_fields=['password'])

            if password_valid:
                # Reset per-account and per-IP failure counters
                student.failed_login_attempts = 0
                student.locked_until = None
                login_ip_reset(request, kind='student_login')

                # Concurrent-session control: kill any previously active session for this student.
                # Defeats parallel-session hijacking — only one device can be logged in at a time.
                if student.current_session_key:
                    try:
                        Session.objects.filter(session_key=student.current_session_key).delete()
                    except Exception:
                        logger.exception('student_login: failed to invalidate prior session')

                # Cycle session key to prevent session fixation
                request.session.cycle_key()
                # Store student info in session
                request.session['student_id'] = student.id
                request.session['student_name'] = student.name
                request.session['student_roll'] = student.roll_number
                request.session['student_school'] = student.school.name
                request.session['student_class'] = student.class_name
                request.session['is_student'] = True
                request.session['must_change_password'] = bool(student.must_change_password)
                # Clean up captcha from session
                request.session.pop('captcha_answer', None)

                # Persist the new session key so we can kill it from elsewhere
                if not request.session.session_key:
                    request.session.save()
                student.current_session_key = request.session.session_key
                student.last_login = timezone.now()
                student.save(update_fields=['last_login', 'failed_login_attempts', 'locked_until', 'current_session_key'])

                log_activity(request, 'STUDENT_LOGIN', f'Student logged in: {student.name} ({student.roll_number})', student=student)

                # Force password change if account still has the default password
                if student.must_change_password:
                    messages.warning(request, 'For security, please change your default password before continuing.')
                    return redirect('student_change_password')

                messages.success(request, f'Welcome, {student.name}!')
                return redirect('student_dashboard')
            else:
                # Failed login — increment both per-account and per-IP counters
                login_ip_register_failure(request, kind='student_login')
                from django.conf import settings as django_settings
                max_attempts = getattr(django_settings, 'ACCOUNT_LOCKOUT_ATTEMPTS', 5)
                lockout_mins = getattr(django_settings, 'ACCOUNT_LOCKOUT_DURATION', 30)
                student.failed_login_attempts += 1
                if student.failed_login_attempts >= max_attempts:
                    student.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_mins)
                    student.save(update_fields=['failed_login_attempts', 'locked_until'])
                    log_activity(request, 'STUDENT_LOGIN', f'Student account locked after {max_attempts} failed attempts: {roll_number}', student=student)
                    messages.error(request, f'Account locked for {lockout_mins} minutes due to too many failed attempts.')
                    return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})
                student.save(update_fields=['failed_login_attempts'])
                log_activity(request, 'STUDENT_LOGIN', f'Failed student login attempt: {roll_number}', student=student)
                messages.error(request, 'Invalid password. Please try again.')
        except Student.DoesNotExist:
            # Critical: this is the path used by roll-number-rotation attacks
            login_ip_register_failure(request, kind='student_login')
            log_activity(request, 'STUDENT_LOGIN', f'Failed student login (roll not found): {roll_number}')
            messages.error(request, 'Invalid roll number or password.')

        return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

    # GET request — generate fresh captcha
    captcha_question = _generate_math_captcha(request)
    return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})


@require_http_methods(["POST"])
def student_logout(request):
    """Handle student logout.
    Invalidates ALL active sessions for this student (kills hijacked parallel sessions).
    """
    # Log + invalidate all sessions for this student before clearing local data
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            log_activity(request, 'STUDENT_LOGOUT', f'Student logged out: {student.name} ({student.roll_number})', student=student)
            # Kill any session we've been tracking for this student
            if student.current_session_key:
                try:
                    Session.objects.filter(session_key=student.current_session_key).delete()
                except Exception:
                    logger.exception('student_logout: failed to delete tracked session')
            # Defence in depth: if the current session key differs (e.g. attacker is logging out),
            # delete that one too
            current_key = request.session.session_key
            if current_key and current_key != student.current_session_key:
                try:
                    Session.objects.filter(session_key=current_key).delete()
                except Exception:
                    pass
            student.current_session_key = None
            student.save(update_fields=['current_session_key'])
        except Student.DoesNotExist:
            pass

    # Flush local session entirely (also drops Django's own session entry)
    request.session.flush()

    messages.success(request, 'You have been logged out successfully.')
    return redirect('student_login')


def get_logged_in_student(request):
    """Return the active Student for the current session, or None.

    Use this instead of `Student.objects.get(id=request.session.get('student_id'))`.
    It verifies the session flag, the student exists, AND `is_active=True`,
    so deactivated accounts cannot continue to use a stale session.
    """
    if not request.session.get('is_student'):
        return None
    sid = request.session.get('student_id')
    if not sid:
        return None
    return Student.objects.filter(id=sid, is_active=True).select_related('school').first()


def student_required(view_func):
    """Decorator to ensure student is logged in.
    Also forces password change if `must_change_password` flag is set.
    Allowed views during forced change: change-password and logout.
    """
    EXEMPT = {'student_change_password', 'student_logout'}

    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_student'):
            messages.error(request, 'Please login to access this page.')
            return redirect('student_login')
        if request.session.get('must_change_password') and view_func.__name__ not in EXEMPT:
            messages.warning(request, 'Please change your default password before continuing.')
            return redirect('student_change_password')
        return view_func(request, *args, **kwargs)
    return wrapper


@require_http_methods(["POST"])
def login_chat_api(request):
    """AJAX endpoint for login page chatbot. No authentication required."""
    from django.core.cache import cache

    # Rate limiting: max 10 requests per minute per IP (unauthenticated endpoint)
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    cache_key = f'login_chat_rl_{client_ip}'
    request_count = cache.get(cache_key, 0)
    if request_count >= 10:
        return JsonResponse({"error": "Too many requests. Please wait a minute."}, status=429)
    cache.set(cache_key, request_count + 1, 60)  # 60-second window

    try:
        body = json.loads(request.body)
        message = body.get("message", "").strip()
        history = body.get("history", [])

        # Validate input
        if not message:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)

        if len(message) > 500:
            return JsonResponse(
                {"error": "Message too long (max 500 characters)."},
                status=400,
            )

        # Check API key

        sarvam_key = os.getenv("SARVAM_API_KEY")
        if not sarvam_key:
            return JsonResponse(
                {"error": "AI service not configured."},
                status=503,
            )

        # Initialize client
        client = SarvamAI(api_subscription_key=sarvam_key)

        # Build conversation
        messages_list = [
            {
                "role": "system",
                "content": (
                    "You are PadhaiWithAI assistant. Help students and parents "
                    "with education and platform-related queries. "
                    "Reply in the same language as the user (Hindi/English). "
                    "Keep responses under 200 words."
                ),
            }
        ]

        # Add last 4 messages
        for msg in history[-4:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                messages_list.append(
                    {
                        "role": role,
                        "content": content[:500],
                    }
                )

        messages_list.append({"role": "user", "content": message})

        # Retry logic
        last_error = None

        for attempt in range(3):
            try:
                response = client.chat.completions(
                    model=os.getenv("SARVAM_MODEL", "sarvam-m"),
                    messages=messages_list,
                    temperature=0.3,
                    top_p=0.9,
                    max_tokens=int(os.getenv("SARVAM_MAX_TOKENS", "4000")),
                )

                _msg = response.choices[0].message
                _raw = _msg.content or getattr(_msg, 'reasoning_content', None) or ''
                reply = _strip_think(_raw.strip())

                return JsonResponse({"reply": reply})

            except ApiError as e:
                last_error = e
                # Retry only on 500
                if e.status_code == 500 and attempt < 2:
                    time.sleep(2)
                    continue
                break

        # If all retries fail
        return JsonResponse(
            {"error": "AI service temporarily unavailable. Please try again."},
            status=502,
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON request."}, status=400)

    except Exception as e:
        return JsonResponse(
            {"error": "Something went wrong. Please try again."},
            status=500,
        )
