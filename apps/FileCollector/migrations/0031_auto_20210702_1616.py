# Generated by Django 3.1.7 on 2021-07-02 14:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0030_auto_20210626_2302'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderproduct',
            name='status',
            field=models.CharField(choices=[('PENDING', 'PENDING'), ('ACTIVE', 'ACTIVE'), ('RENDER', 'RENDER'), ('FAILED', 'FAILED'), ('COMPLETE', 'COMPLETE'), ('IDLE', 'IDLE'), ('READY', 'READY'), ('DELIVERED', 'DELIVERED')], default='PENDING', max_length=15),
        ),
    ]