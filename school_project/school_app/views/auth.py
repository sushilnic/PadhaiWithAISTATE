"""
Authentication views: login, logout, password change, student auth.
"""
from .utils import *
from .utils import _strip_think, _generate_math_captcha
from .hierarchy import get_user_hierarchy


def is_system_admin(user):
    return user.is_authenticated and user.is_system_admin

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # Check account lockout
            try:
                target_user = CustomUser.objects.get(email=email)
                if target_user.locked_until and target_user.locked_until > timezone.now():
                    remaining = int((target_user.locked_until - timezone.now()).total_seconds() // 60) + 1
                    log_activity(request, 'LOGIN', f'Login blocked (account locked): {email}')
                    messages.error(request, f'Account locked. Try again in {remaining} minutes.')
                    return render(request, 'school_app/login.html', {'form': form})
                # Clear expired lock
                if target_user.locked_until and target_user.locked_until <= timezone.now():
                    target_user.locked_until = None
                    target_user.failed_login_attempts = 0
                    target_user.save(update_fields=['locked_until', 'failed_login_attempts'])
            except CustomUser.DoesNotExist:
                target_user = None

            user = authenticate(request, email=email, password=password)
            if user is not None:
                # Reset failed attempts on success
                user.failed_login_attempts = 0
                user.locked_until = None
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
                # Failed login — increment counter and possibly lock
                log_activity(request, 'LOGIN', f'Failed login attempt: {email}')
                if target_user:
                    from django.conf import settings as django_settings
                    max_attempts = getattr(django_settings, 'ACCOUNT_LOCKOUT_ATTEMPTS', 5)
                    lockout_mins = getattr(django_settings, 'ACCOUNT_LOCKOUT_DURATION', 30)
                    target_user.failed_login_attempts += 1
                    if target_user.failed_login_attempts >= max_attempts:
                        target_user.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_mins)
                        target_user.save(update_fields=['failed_login_attempts', 'locked_until'])
                        log_activity(request, 'LOGIN', f'Account locked after {max_attempts} failed attempts: {email}')
                        messages.error(request, f'Account locked for {lockout_mins} minutes due to too many failed attempts.')
                        return render(request, 'school_app/login.html', {'form': form})
                    target_user.save(update_fields=['failed_login_attempts'])
                messages.error(request, 'Invalid credentials')
    else:
        form = LoginForm()
    return render(request, 'school_app/login.html', {'form': form})


@require_http_methods(["POST"])
def logout_view(request):
    if request.user.is_authenticated:
        log_activity(request, 'LOGOUT', f'User logged out: {request.user.email}')
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
        roll_number = request.POST.get('roll_number', '').strip()
        password = request.POST.get('password', '').strip()
        captcha_input = request.POST.get('captcha', '').strip()

        # Validate captcha — pop removes the old answer so it cannot be reused
        expected = request.session.pop('captcha_answer', None)
        request.session.modified = True   # force save so the pop is persisted
        captcha_question = _generate_math_captcha(request)  # fresh question for next attempt

        if not captcha_input or expected is None:
            messages.error(request, 'Please solve the math question.')
            return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

        try:
            if int(captcha_input) != int(expected):
                messages.error(request, 'Wrong answer to the math question. Please try again.')
                return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})
        except (ValueError, TypeError):
            messages.error(request, 'Please enter a valid number for the math question.')
            return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

        if not roll_number or not password:
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
                # Reset failed attempts
                student.failed_login_attempts = 0
                student.locked_until = None
                # Cycle session key to prevent session fixation
                request.session.cycle_key()
                # Store student info in session
                request.session['student_id'] = student.id
                request.session['student_name'] = student.name
                request.session['student_roll'] = student.roll_number
                request.session['student_school'] = student.school.name
                request.session['student_class'] = student.class_name
                request.session['is_student'] = True
                # Clean up captcha from session
                request.session.pop('captcha_answer', None)

                # Update last login
                student.last_login = timezone.now()
                student.save(update_fields=['last_login', 'failed_login_attempts', 'locked_until'])

                log_activity(request, 'STUDENT_LOGIN', f'Student logged in: {student.name} ({student.roll_number})', student=student)
                messages.success(request, f'Welcome, {student.name}!')
                return redirect('student_dashboard')
            else:
                # Failed login — increment counter
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
            log_activity(request, 'STUDENT_LOGIN', f'Failed student login (roll not found): {roll_number}')
            messages.error(request, 'Invalid roll number or password.')

        return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})

    # GET request — generate fresh captcha
    captcha_question = _generate_math_captcha(request)
    return render(request, 'school_app/student/student_login.html', {'captcha_question': captcha_question})


@require_http_methods(["POST"])
def student_logout(request):
    """Handle student logout."""
    # Log before clearing session
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            log_activity(request, 'STUDENT_LOGOUT', f'Student logged out: {student.name} ({student.roll_number})', student=student)
        except Student.DoesNotExist:
            pass
    # Clear student session data
    keys_to_remove = ['student_id', 'student_name', 'student_roll', 'student_school', 'student_class', 'is_student']
    for key in keys_to_remove:
        request.session.pop(key, None)

    messages.success(request, 'You have been logged out successfully.')
    return redirect('student_login')


def student_required(view_func):
    """Decorator to ensure student is logged in."""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_student'):
            messages.error(request, 'Please login to access this page.')
            return redirect('student_login')
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
                    messages=messages_list,
                    temperature=0.3,
                    top_p=0.9,
                )

                reply = _strip_think(response.choices[0].message.content.strip())

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
