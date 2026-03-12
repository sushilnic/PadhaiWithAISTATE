"""
Management command to fix database issues after restoring from backup.
Run this command after restoring database from live server.

Usage:
    python manage.py fix_after_restore
    python manage.py fix_after_restore --reset-password admin@example.com newpassword123
    python manage.py fix_after_restore --create-superuser
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.sessions.models import Session
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from school_app.models import CustomUser, School, Block, District


class Command(BaseCommand):
    help = 'Fix database issues after restoring from backup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-password',
            nargs=2,
            metavar=('EMAIL', 'PASSWORD'),
            help='Reset password for a specific user'
        )
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create a new superuser if none exists'
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check for issues, do not fix'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE('PadhaiWithAI - Database Fix After Restore'))
        self.stdout.write(self.style.NOTICE('=' * 60))

        issues_found = 0
        issues_fixed = 0

        # Step 1: Clear old sessions
        self.stdout.write('\n[1] Clearing old sessions...')
        try:
            session_count = Session.objects.count()
            if session_count > 0:
                issues_found += 1
                if not options['check_only']:
                    Session.objects.all().delete()
                    issues_fixed += 1
                    self.stdout.write(self.style.SUCCESS(f'    Deleted {session_count} old sessions'))
                else:
                    self.stdout.write(self.style.WARNING(f'    Found {session_count} old sessions (not deleted in check mode)'))
            else:
                self.stdout.write(self.style.SUCCESS('    No old sessions found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'    Error: {e}'))

        # Step 2: Clear CAPTCHA store
        self.stdout.write('\n[2] Clearing CAPTCHA store...')
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM captcha_captchastore")
                self.stdout.write(self.style.SUCCESS('    CAPTCHA store cleared'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'    Skipped (table may not exist): {e}'))

        # Step 3: Check and fix inactive users
        self.stdout.write('\n[3] Checking user active status...')
        inactive_users = CustomUser.objects.filter(is_active=False)
        if inactive_users.exists():
            issues_found += inactive_users.count()
            if not options['check_only']:
                count = inactive_users.update(is_active=True)
                issues_fixed += count
                self.stdout.write(self.style.SUCCESS(f'    Activated {count} inactive users'))
            else:
                self.stdout.write(self.style.WARNING(f'    Found {inactive_users.count()} inactive users'))
        else:
            self.stdout.write(self.style.SUCCESS('    All users are active'))

        # Step 4: Check password hashing
        self.stdout.write('\n[4] Checking password hashing...')
        users_with_bad_passwords = []
        for user in CustomUser.objects.all():
            if not user.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$', 'sha1$', 'md5$', 'crypt$')):
                users_with_bad_passwords.append(user)

        if users_with_bad_passwords:
            issues_found += len(users_with_bad_passwords)
            self.stdout.write(self.style.ERROR(f'    Found {len(users_with_bad_passwords)} users with invalid password format:'))
            for user in users_with_bad_passwords[:10]:  # Show first 10
                self.stdout.write(self.style.ERROR(f'      - {user.email} (ID: {user.id})'))
            if len(users_with_bad_passwords) > 10:
                self.stdout.write(self.style.ERROR(f'      ... and {len(users_with_bad_passwords) - 10} more'))
            self.stdout.write(self.style.WARNING('    Use --reset-password to fix individual users'))
        else:
            self.stdout.write(self.style.SUCCESS('    All passwords are properly hashed'))

        # Step 5: Fix user role flags
        self.stdout.write('\n[5] Fixing user role flags...')

        # School admins
        school_admins = CustomUser.objects.filter(
            administered_school__isnull=False,
            is_school_user=False
        )
        if school_admins.exists():
            issues_found += school_admins.count()
            if not options['check_only']:
                count = school_admins.update(is_school_user=True)
                issues_fixed += count
                self.stdout.write(self.style.SUCCESS(f'    Fixed {count} school admin role flags'))
            else:
                self.stdout.write(self.style.WARNING(f'    Found {school_admins.count()} school admins without is_school_user=True'))

        # Block admins
        block_admins = CustomUser.objects.filter(
            block_admin__isnull=False,
            is_block_user=False
        )
        if block_admins.exists():
            issues_found += block_admins.count()
            if not options['check_only']:
                count = block_admins.update(is_block_user=True)
                issues_fixed += count
                self.stdout.write(self.style.SUCCESS(f'    Fixed {count} block admin role flags'))

        # District admins
        district_admins = CustomUser.objects.filter(
            district_admin__isnull=False,
            is_district_user=False
        )
        if district_admins.exists():
            issues_found += district_admins.count()
            if not options['check_only']:
                count = district_admins.update(is_district_user=True)
                issues_fixed += count
                self.stdout.write(self.style.SUCCESS(f'    Fixed {count} district admin role flags'))

        if not school_admins.exists() and not block_admins.exists() and not district_admins.exists():
            self.stdout.write(self.style.SUCCESS('    All role flags are correct'))

        # Step 6: Ensure superuser exists
        self.stdout.write('\n[6] Checking superuser...')
        superusers = CustomUser.objects.filter(is_superuser=True, is_active=True)
        if not superusers.exists():
            issues_found += 1
            if options['create_superuser'] and not options['check_only']:
                user = CustomUser.objects.create_superuser(
                    email='admin@padhaiwithai.com',
                    password='Admin@123'
                )
                issues_fixed += 1
                self.stdout.write(self.style.SUCCESS('    Created new superuser:'))
                self.stdout.write(self.style.SUCCESS('      Email: admin@padhaiwithai.com'))
                self.stdout.write(self.style.SUCCESS('      Password: Admin@123'))
                self.stdout.write(self.style.WARNING('      ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!'))
            else:
                self.stdout.write(self.style.ERROR('    No active superuser found!'))
                self.stdout.write(self.style.WARNING('    Use --create-superuser to create one'))
        else:
            self.stdout.write(self.style.SUCCESS(f'    Found {superusers.count()} active superuser(s)'))
            for su in superusers:
                self.stdout.write(f'      - {su.email}')

        # Step 7: Fix superuser flags
        self.stdout.write('\n[7] Fixing superuser flags...')
        superusers_needing_fix = CustomUser.objects.filter(
            is_superuser=True
        ).exclude(
            is_staff=True, is_system_admin=True
        )
        if superusers_needing_fix.exists():
            issues_found += superusers_needing_fix.count()
            if not options['check_only']:
                count = superusers_needing_fix.update(
                    is_staff=True,
                    is_system_admin=True,
                    is_active=True
                )
                issues_fixed += count
                self.stdout.write(self.style.SUCCESS(f'    Fixed {count} superuser flag(s)'))
        else:
            self.stdout.write(self.style.SUCCESS('    All superuser flags are correct'))

        # Step 8: Reset specific user password if requested
        if options['reset_password']:
            email, new_password = options['reset_password']
            self.stdout.write(f'\n[8] Resetting password for {email}...')
            try:
                user = CustomUser.objects.get(email=email)
                user.password = make_password(new_password)
                user.is_active = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'    Password reset successfully for {email}'))
            except CustomUser.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'    User not found: {email}'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.NOTICE('SUMMARY'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'Issues found: {issues_found}')
        if not options['check_only']:
            self.stdout.write(f'Issues fixed: {issues_fixed}')
        else:
            self.stdout.write(self.style.WARNING('Check mode - no changes made'))

        # Show user list
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('Current Users (first 10):')
        self.stdout.write('-' * 60)
        self.stdout.write(f'{"ID":<5} {"Email":<30} {"Active":<8} {"Super":<8} {"Staff":<8}')
        self.stdout.write('-' * 60)
        for user in CustomUser.objects.all()[:10]:
            self.stdout.write(
                f'{user.id:<5} {user.email[:28]:<30} '
                f'{"Yes" if user.is_active else "No":<8} '
                f'{"Yes" if user.is_superuser else "No":<8} '
                f'{"Yes" if user.is_staff else "No":<8}'
            )

        self.stdout.write('\n' + self.style.SUCCESS('Done!'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('  1. Run: python manage.py migrate')
        self.stdout.write('  2. Run: python manage.py collectstatic --noinput')
        self.stdout.write('  3. Restart the server')
