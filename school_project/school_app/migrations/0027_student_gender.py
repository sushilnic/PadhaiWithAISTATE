from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0026_aisathichapter_description_starter_questions'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='gender',
            field=models.CharField(
                blank=True,
                choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
                default='',
                max_length=1,
                verbose_name='Gender',
            ),
        ),
    ]
