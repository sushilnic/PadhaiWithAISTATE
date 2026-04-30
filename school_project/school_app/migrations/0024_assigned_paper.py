import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("school_app", "0023_ai_sathi_seed_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssignedPaper",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("class_name", models.CharField(max_length=5)),
                ("due_date", models.DateTimeField(blank=True, null=True)),
                ("time_limit", models.PositiveIntegerField(blank=True, help_text="minutes", null=True)),
                ("instructions", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Assigned Paper", "verbose_name_plural": "Assigned Papers", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="StudentPaperAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("answers", models.JSONField(default=dict)),
                ("score", models.FloatField(blank=True, null=True)),
                ("max_score", models.FloatField(blank=True, null=True)),
                ("is_submitted", models.BooleanField(default=False)),
            ],
            options={"verbose_name": "Student Paper Attempt", "ordering": ["-started_at"]},
        ),
        migrations.AddField(
            model_name="assignedpaper",
            name="assigned_by",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="paper_assignments", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="assignedpaper",
            name="question_paper",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="school_app.questionpaperhistory"),
        ),
        migrations.AddField(
            model_name="assignedpaper",
            name="school",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assigned_papers", to="school_app.school"),
        ),
        migrations.AddField(
            model_name="studentpaperattempt",
            name="assigned_paper",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="school_app.assignedpaper"),
        ),
        migrations.AddField(
            model_name="studentpaperattempt",
            name="student",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="paper_attempts", to="school_app.student"),
        ),
        migrations.AlterUniqueTogether(
            name="studentpaperattempt",
            unique_together={("assigned_paper", "student")},
        ),
    ]
