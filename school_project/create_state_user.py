import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_project.settings')
django.setup()

from school_app.models import CustomUser, State

  # Configuration
EMAIL = 'rajasthan@padhaiwithai.in'
PASSWORD = 'nic@123'
#   STATE_NAME_EN = 'Rajasthan'
#   STATE_NAME_HI = 'राजस्थान'
#   STATE_CODE = 'RJ'

  # Create user
user, created = CustomUser.objects.get_or_create(
      email=EMAIL,
      defaults={
          'is_state_user': 1,
          'is_school_user': 0,
          'is_staff': 0,
          'is_active': 1,
          'first_name': 'Rajasthan',
          'last_name': 'RJ'
      }
  )

if created:
      user.set_password(PASSWORD)
      user.save()
      print(f"✓ User created: {EMAIL}")
else:
      print(f"User already exists: {EMAIL}")

#   # Create state
#   state, created = State.objects.get_or_create(
#       code=STATE_CODE,
#       defaults={
#           'name_english': STATE_NAME_EN,
#           'name_hindi': STATE_NAME_HI,
#           'admin': user,
#           'is_active': True
#       }
#   )

#   if created:
#       print(f"✓ State created: {STATE_NAME_EN}")
#   else:
#       state.admin = user
#       state.save()
#       print(f"State already exists, linked to user")

print(f"\n Login with:")
print(f"   Email: {EMAIL}")
print(f"   Password: {PASSWORD}")