from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0025_ai_sathi_improvements'),
    ]

    operations = [
        migrations.AddField(
            model_name='aisathichapter',
            name='description',
            field=models.TextField(
                blank=True, default='',
                help_text='Brief chapter topics/objectives for AI context'
            ),
        ),
        migrations.AddField(
            model_name='aisathichapter',
            name='starter_questions',
            field=models.JSONField(
                blank=True, default=list,
                help_text='Suggested starter questions list'
            ),
        ),
    ]
