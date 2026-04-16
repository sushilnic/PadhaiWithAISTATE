from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0021_questionpaperhistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='AISathiClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveSmallIntegerField(unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'AI Sathi Class',
                'verbose_name_plural': 'AI Sathi Classes',
                'ordering': ['order', 'number'],
            },
        ),
        migrations.CreateModel(
            name='AISathiSubject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('class_ref', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subjects',
                    to='school_app.aisathiclass',
                )),
            ],
            options={
                'verbose_name': 'AI Sathi Subject',
                'verbose_name_plural': 'AI Sathi Subjects',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.AddConstraint(
            model_name='aisathisubject',
            constraint=models.UniqueConstraint(
                fields=['class_ref', 'name'],
                name='unique_class_subject',
            ),
        ),
        migrations.CreateModel(
            name='AISathiChapter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('subject', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chapters',
                    to='school_app.aisathisubject',
                )),
            ],
            options={
                'verbose_name': 'AI Sathi Chapter',
                'verbose_name_plural': 'AI Sathi Chapters',
                'ordering': ['order', 'id'],
            },
        ),
    ]
