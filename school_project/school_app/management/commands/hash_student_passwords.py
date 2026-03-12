"""
Management command to hash all plain text student passwords.
Run after server restore or code deployment:
    python manage.py hash_student_passwords
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from school_app.models import Student


class Command(BaseCommand):
    help = 'Hash all plain text student passwords using PBKDF2'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show count of passwords to hash without making changes',
        )

    def handle(self, *args, **options):
        # Find students with plain text passwords (not hashed)
        students = Student.objects.filter(
            password__isnull=False,
        ).exclude(
            password=''
        ).exclude(
            password__startswith='pbkdf2_sha256$'
        ).exclude(
            password__startswith='bcrypt'
        ).exclude(
            password__startswith='argon2'
        )

        total = students.count()
        self.stdout.write(f'Found {total} students with plain text passwords.')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry run — no changes made.'))
            return

        if total == 0:
            self.stdout.write(self.style.SUCCESS('All passwords are already hashed.'))
            return

        hashed = 0
        batch_size = 500
        student_ids = list(students.values_list('id', flat=True))

        for i in range(0, len(student_ids), batch_size):
            batch_ids = student_ids[i:i + batch_size]
            batch = Student.objects.filter(id__in=batch_ids)

            for student in batch:
                student.password = make_password(student.password)

            Student.objects.bulk_update(batch, ['password'], batch_size=batch_size)
            hashed += len(batch_ids)
            self.stdout.write(f'  Hashed {hashed}/{total} ...')

        self.stdout.write(self.style.SUCCESS(f'Done. {hashed} passwords hashed successfully.'))
