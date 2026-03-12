# Generated manually - Alter topic field to allow longer chapter names

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0013_practicetest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='practicetest',
            name='topic',
            field=models.CharField(max_length=200),
        ),
    ]
