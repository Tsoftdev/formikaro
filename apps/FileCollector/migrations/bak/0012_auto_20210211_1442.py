# Generated by Django 3.1.6 on 2021-02-11 12:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0011_client_shop_username'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='billing_address',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_reference_number',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]