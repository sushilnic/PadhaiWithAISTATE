"""
Custom authentication backends for PadhaiWithAI.

- EmailOrUsernameBackend: lets a user log in with either their email OR their
  username. Tried in that order (email first — more distinct + universally set).
  Both lookups are case-insensitive.

To enable, add to settings.py:

    AUTHENTICATION_BACKENDS = [
        'school_app.auth_backends.EmailOrUsernameBackend',
        'django.contrib.auth.backends.ModelBackend',  # keep as fallback
    ]
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate against either the `email` field or the `username` field.

    Django's convention: whatever the login form sends is passed as `username`
    into `authenticate(...)`. This backend treats that value as an
    'identifier' and tries email first, then username. Case-insensitive.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Django auth expects the input to be called `username` even when we
        # want it to also match an email. We accept an `email` kwarg for
        # convenience (older callers pass email=...).
        identifier = username or kwargs.get('email') or kwargs.get('identifier')
        if not identifier or not password:
            return None

        UserModel = get_user_model()
        try:
            # Case-insensitive OR match — safe even if two records share the
            # same email/username casing because both fields are unique().
            user = (UserModel.objects
                    .filter(Q(email__iexact=identifier) | Q(username__iexact=identifier))
                    .first())
        except UserModel.DoesNotExist:
            # Mimic ModelBackend's timing-attack mitigation
            UserModel().set_password(password)
            return None

        if user is None:
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
