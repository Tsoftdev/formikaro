# Generated by Django 3.1.5 on 2021-02-08 17:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ProductManager', '0002_auto_20210202_1746'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='resolution',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.PROTECT, to='ProductManager.resolution'),
        ),
    ]
