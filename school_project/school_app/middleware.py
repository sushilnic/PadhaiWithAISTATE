from datetime import timedelta
from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone


class SecurityMiddleware:
    """Handles force password change and password expiry checks."""

    EXEMPT_URLS = [
        '/login/',
        '/logout/',
        '/user/change-password/',
        '/student/login/',
        '/student/logout/',
        '/captcha/',
        '/api/login-chat/',
        '/static/',
        '/media/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path

            # Skip exempt URLs
            if not any(path.startswith(url) for url in self.EXEMPT_URLS):
                # Check force password change
                if request.user.must_change_password:
                    return redirect('change_password')

                # Check password expiry for admin roles
                expiry_days = getattr(settings, 'PASSWORD_EXPIRY_DAYS', 90)
                if self._is_admin_role(request.user) and request.user.password_changed_at:
                    expiry_date = request.user.password_changed_at + timedelta(days=expiry_days)
                    if timezone.now() > expiry_date:
                        request.user.must_change_password = True
                        request.user.save(update_fields=['must_change_password'])
                        return redirect('change_password')

        response = self.get_response(request)

        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response

    def _is_admin_role(self, user):
        return (user.is_system_admin or user.is_state_user or
                user.is_district_user or user.is_block_user)
