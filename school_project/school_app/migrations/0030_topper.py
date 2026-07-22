from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0029_student_current_session_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='Topper',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('caption', models.CharField(blank=True, help_text="e.g. 'Class 10 — 98% in Maths'", max_length=255, null=True)),
                ('image', models.ImageField(max_length=200, upload_to='toppers/')),
                ('week_start', models.DateField()),
                ('week_end', models.DateField()),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL,
                                                  related_name='created_toppers', to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL,
                                              related_name='toppers', to='school_app.school')),
            ],
            options={
                'verbose_name': 'Topper',
                'verbose_name_plural': 'Toppers',
                'db_table': 'school_app_topper',
                'ordering': ['order', '-created_at'],
                'indexes': [models.Index(fields=['week_start', 'week_end', 'is_active'],
                                         name='idx_topper_week_active')],
            },
        ),
    ]
