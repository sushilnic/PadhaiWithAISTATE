from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0024_assigned_paper'),
    ]

    operations = [
        migrations.AddField(
            model_name='aisathichapter',
            name='description',
            field=models.TextField(blank=True, default='', help_text='Brief chapter topics/objectives for AI context'),
        ),
        migrations.AddField(
            model_name='aisathichapter',
            name='starter_questions',
            field=models.JSONField(blank=True, default=list, help_text='Suggested starter questions list'),
        ),
        migrations.CreateModel(
            name='AISathiChatSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(db_index=True, max_length=100)),
                ('class_level', models.CharField(blank=True, max_length=10)),
                ('subject', models.CharField(blank=True, max_length=100)),
                ('chapter', models.CharField(blank=True, max_length=300)),
                ('language', models.CharField(default='Hindi', max_length=50)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_sathi_sessions', to='school_app.student')),
            ],
            options={
                'verbose_name': 'AI Sathi Chat Session',
                'verbose_name_plural': 'AI Sathi Chat Sessions',
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='AISathiMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=20)),
                ('content', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('rating', models.SmallIntegerField(blank=True, null=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='school_app.aisathichatsession')),
            ],
            options={
                'verbose_name': 'AI Sathi Message',
                'verbose_name_plural': 'AI Sathi Messages',
                'ordering': ['timestamp'],
            },
        ),
    ]
