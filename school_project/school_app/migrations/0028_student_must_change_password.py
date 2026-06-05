from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0027_student_gender'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='must_change_password',
            field=models.BooleanField(
                default=False,
                help_text='Force change on next login (default-password accounts)',
            ),
        ),
    ]
