# Generated by Django 3.1.5 on 2021-04-26 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0010_auto_20210426_1545'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='status',
            field=models.CharField(choices=[('ESTIMATE', 'ESTIMATE'), ('ACTIVE', 'ACTIVE'), ('ONHOLD', 'ONHOLD'), ('CLIENT', 'CLIENT'), ('FAILED', 'FAILED'), ('COMPLETE', 'COMPLETE'), ('DELIVERED', 'DELIVERED'), ('PAID', 'PAID')], default='PENDING', max_length=50),
        ),
    ]
