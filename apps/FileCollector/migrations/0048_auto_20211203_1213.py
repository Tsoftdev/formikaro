# Generated by Django 3.1.5 on 2021-12-03 11:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0047_auto_20211130_1520'),
    ]

    operations = [
        migrations.RenameField(
            model_name='projectvideo',
            old_name='runtime',
            new_name='duration',
        ),
        migrations.AddField(
            model_name='video',
            name='duration',
            field=models.IntegerField(blank=True, default=0),
        ),
    ]