# Generated by Django 3.1.5 on 2021-04-08 09:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0003_auto_20210406_0929'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='status',
            field=models.CharField(choices=[('PENDING', 'PENDING'), ('UPLOADING NOW', 'UPLOADING NOW'), ('COMPLETE', 'COMPLETE'), ('FAILED', 'FAILED')], default='PENDING', max_length=50),
        ),
    ]
