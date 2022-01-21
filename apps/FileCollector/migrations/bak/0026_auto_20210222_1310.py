# Generated by Django 3.1.5 on 2021-02-22 12:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0025_auto_20210222_1221'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderproduct',
            name='discount',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='orderproduct',
            name='unitprice',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
