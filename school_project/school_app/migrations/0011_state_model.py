# Generated manually for State, District, Block models and hierarchy
# This migration has already been applied to the database

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0010_remove_marks_test_number'),
    ]

    operations = [
        # Add role fields to CustomUser
        migrations.AddField(
            model_name='customuser',
            name='is_state_user',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='is_district_user',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='is_block_user',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='is_school_user',
            field=models.BooleanField(default=True),
        ),

        # Create State model
        migrations.CreateModel(
            name='State',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_english', models.CharField(max_length=100)),
                ('name_hindi', models.CharField(max_length=100)),
                ('code', models.CharField(help_text='State code (e.g., RJ for Rajasthan)', max_length=10, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('admin', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='state_admin', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'State',
                'verbose_name_plural': 'States',
                'ordering': ['name_english'],
            },
        ),

        # Create District model
        migrations.CreateModel(
            name='District',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_english', models.CharField(max_length=100)),
                ('name_hindi', models.CharField(max_length=100)),
                ('state', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='districts', to='school_app.state')),
                ('admin', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='district_admin', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'District',
                'verbose_name_plural': 'Districts',
                'ordering': ['name_english'],
            },
        ),

        # Create Block model
        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_english', models.CharField(max_length=100)),
                ('name_hindi', models.CharField(max_length=100)),
                ('district', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocks', to='school_app.district')),
                ('admin', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='block_admin', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Block',
                'verbose_name_plural': 'Blocks',
                'ordering': ['name_english'],
            },
        ),

        # Add block field to School
        migrations.AddField(
            model_name='school',
            name='block',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='block_schools', to='school_app.block'),
        ),

        # Add nic_code to School
        migrations.AddField(
            model_name='school',
            name='nic_code',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),

        # Add Attendance model
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(auto_now_add=True)),
                ('is_present', models.BooleanField(default=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='school_app.student')),
            ],
            options={
                'verbose_name': 'Attendance',
                'verbose_name_plural': 'Attendance Records',
                'unique_together': {('student', 'date')},
            },
        ),

        # Update Student model - add related_name
        migrations.AlterField(
            model_name='student',
            name='school',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='school_app.school'),
        ),

        # Update Marks model - add related_name
        migrations.AlterField(
            model_name='marks',
            name='student',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marks_records', to='school_app.student'),
        ),
    ]
