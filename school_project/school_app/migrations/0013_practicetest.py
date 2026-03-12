# Generated manually for PracticeTest model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0012_add_student_auth_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='PracticeTest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(choices=[
                    ('addition', 'Addition'),
                    ('subtraction', 'Subtraction'),
                    ('multiplication', 'Multiplication'),
                    ('division', 'Division'),
                    ('fractions', 'Fractions'),
                    ('decimals', 'Decimals'),
                    ('percentages', 'Percentages'),
                    ('algebra', 'Algebra'),
                    ('geometry', 'Geometry'),
                    ('mixed', 'Mixed Topics'),
                ], max_length=50)),
                ('difficulty', models.CharField(choices=[
                    ('easy', 'Easy'),
                    ('medium', 'Medium'),
                    ('hard', 'Hard'),
                ], default='medium', max_length=20)),
                ('total_questions', models.IntegerField(default=10)),
                ('correct_answers', models.IntegerField(default=0)),
                ('wrong_answers', models.IntegerField(default=0)),
                ('time_taken', models.IntegerField(blank=True, help_text='Time in seconds', null=True)),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='practice_tests', to='school_app.student')),
            ],
            options={
                'verbose_name': 'Practice Test',
                'verbose_name_plural': 'Practice Tests',
                'ordering': ['-attempted_at'],
            },
        ),
        migrations.AddIndex(
            model_name='practicetest',
            index=models.Index(fields=['student', 'topic'], name='school_app__student_8c1f3e_idx'),
        ),
        migrations.AddIndex(
            model_name='practicetest',
            index=models.Index(fields=['attempted_at'], name='school_app__attempt_4f8c2a_idx'),
        ),
    ]
