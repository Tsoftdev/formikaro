from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('ProductManager', '0006_auto_20220113_2300'),
    ]

    operations = [
        migrations.AddField(
            model_name='language',
            name='system_language',
            field=models.BooleanField(default=False),
        ),
    ]
