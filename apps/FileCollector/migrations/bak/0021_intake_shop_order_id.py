# Generated by Django 3.1.5 on 2021-02-15 13:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0020_auto_20210215_1331'),
    ]

    operations = [
        migrations.AddField(
            model_name='intake',
            name='shop_order_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
