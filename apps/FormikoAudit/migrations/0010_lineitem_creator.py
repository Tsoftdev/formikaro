# Generated by Django 3.1.5 on 2021-09-07 13:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0043_projectmanager_is_manager'),
        ('FormikoAudit', '0009_auto_20210907_1118'),
    ]

    operations = [
        migrations.AddField(
            model_name='lineitem',
            name='creator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='FileCollector.projectmanager'),
        ),
    ]
