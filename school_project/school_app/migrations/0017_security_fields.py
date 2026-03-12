from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0016_add_activity_log'),
    ]

    operations = [
        # CustomUser security fields
        migrations.AddField(
            model_name='customuser',
            name='failed_login_attempts',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='customuser',
            name='locked_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='must_change_password',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='password_changed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='current_session_key',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        # Student security fields
        migrations.AddField(
            model_name='student',
            name='failed_login_attempts',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='student',
            name='locked_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
