# Generated by Django 3.1.5 on 2021-03-01 11:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('FormikoBot', '0009_auto_20210301_1202'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='assetpreset',
            table='fo_asset_preset',
        ),
        migrations.AlterModelTable(
            name='assettype',
            table='fo_asset_type',
        ),
    ]
