"""Add is_active and created_at fields to District, Block, and School models."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0014_alter_practicetest_topic'),
    ]

    operations = [
        migrations.AddField(
            model_name='district',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='district',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='block',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='block',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='school',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
