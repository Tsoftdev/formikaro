# Generated by Django 3.1.5 on 2021-09-06 12:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0033_auto_20210906_1353'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='folderid',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
