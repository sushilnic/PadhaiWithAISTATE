from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('school_app', '0017_security_fields'),
    ]
    operations = [
        migrations.AddField(
            model_name='test',
            name='district',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tests',
                to='school_app.district',
            ),
        ),
    ]
