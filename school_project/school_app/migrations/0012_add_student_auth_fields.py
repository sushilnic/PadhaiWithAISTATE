# Generated manually for Student authentication fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0011_state_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='password',
            field=models.CharField(blank=True, help_text='Student login password', max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='student',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='student',
            name='last_login',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
