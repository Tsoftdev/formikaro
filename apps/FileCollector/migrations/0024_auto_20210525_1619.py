# Generated by Django 3.1.5 on 2021-05-25 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0023_video_size'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='is_bot',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='projectmanager',
            name='is_bot',
            field=models.BooleanField(default=False),
        ),
    ]
