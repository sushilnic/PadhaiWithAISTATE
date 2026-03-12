from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0019_academiccalendarevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='max_marks',
            field=models.FloatField(default=100),
            preserve_default=False,
        ),
    ]
