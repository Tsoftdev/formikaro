# Generated by Django 3.1.4 on 2021-01-29 17:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0004_auto_20210129_1845'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='gender',
            field=models.CharField(choices=[('female', 'female'), ('male', 'male'), ('undefined', 'undefined')], default='undefined', max_length=15),
        ),
        migrations.AddField(
            model_name='projectmanager',
            name='gender',
            field=models.CharField(choices=[('female', 'female'), ('male', 'male'), ('undefined', 'undefined')], default='undefined', max_length=15),
        ),
    ]
