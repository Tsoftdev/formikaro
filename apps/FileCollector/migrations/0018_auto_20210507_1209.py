# Generated by Django 3.1.5 on 2021-05-07 10:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0017_orderproduct_orderitemid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderproduct',
            name='orderItemID',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=10),
        ),
    ]
