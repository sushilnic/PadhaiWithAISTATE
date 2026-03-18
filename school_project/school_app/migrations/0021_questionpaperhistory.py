from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0020_add_max_marks_to_test'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionPaperHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=100)),
                ('chapter', models.CharField(max_length=200)),
                ('class_name', models.CharField(max_length=5)),
                ('language', models.CharField(max_length=20)),
                ('difficulty', models.CharField(
                    choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard'), ('Mixed', 'Mixed')],
                    default='Medium', max_length=10,
                )),
                ('total_marks', models.PositiveIntegerField()),
                ('time_allowed', models.PositiveIntegerField(help_text='minutes')),
                ('paper_json', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='question_papers',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Question Paper History',
                'verbose_name_plural': 'Question Paper Histories',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user', '-created_at'], name='school_app_qph_user_idx'),
                ],
            },
        ),
    ]
