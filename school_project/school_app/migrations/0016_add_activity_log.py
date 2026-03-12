from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0015_add_management_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_email', models.CharField(blank=True, default='', max_length=255)),
                ('user_role', models.CharField(blank=True, default='', max_length=50)),
                ('action_type', models.CharField(choices=[
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
                ], max_length=20)),
                ('description', models.TextField(blank=True, default='')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('district', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activity_logs', to='school_app.district')),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activity_logs', to='school_app.student')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activity_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Activity Log',
                'verbose_name_plural': 'Activity Logs',
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['-timestamp'], name='school_app__timesta_idx'),
                    models.Index(fields=['district', '-timestamp'], name='school_app__distric_idx'),
                    models.Index(fields=['action_type'], name='school_app__action__idx'),
                ],
            },
        ),
    ]
