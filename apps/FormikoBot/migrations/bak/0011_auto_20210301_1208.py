# Generated by Django 3.1.5 on 2021-03-01 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FormikoBot', '0010_auto_20210301_1207'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='source',
            field=models.CharField(choices=[('EXAU', 'External auto'), ('EXMA', 'External manual'), ('INAU', 'Internal auto'), ('INMA', 'Internal manual')], default='EXAU', max_length=15),
        ),
    ]
