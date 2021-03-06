# Generated by Django 3.1.5 on 2021-04-26 13:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0007_auto_20210426_1535'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='change_log',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='FileCollector.client'),
        ),
        migrations.AlterField(
            model_name='project',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='FileCollector.company'),
        ),
    ]
