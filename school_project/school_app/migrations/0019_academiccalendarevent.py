from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0018_test_district'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicCalendarEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('event_type', models.CharField(
                    choices=[
                        ('teaching', 'Teaching / Syllabus'),
                        ('exam',     'Exam / Assessment'),
                        ('holiday',  'Holiday'),
                        ('meeting',  'Meeting'),
                        ('other',    'Other'),
                    ],
                    default='teaching',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ('district', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='calendar_events',
                    to='school_app.district',
                )),
            ],
            options={'ordering': ['start_date']},
        ),
    ]
