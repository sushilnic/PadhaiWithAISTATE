from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0028_student_must_change_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='current_session_key',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=40,
                help_text='Active session key — used to enforce single-session and kill hijacked parallel sessions',
            ),
        ),
    ]
