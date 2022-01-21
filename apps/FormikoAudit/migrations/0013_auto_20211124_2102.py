# Generated by Django 3.1.5 on 2021-11-24 13:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0044_merge_20211005_2103'),
        ('FormikoAudit', '0012_auto_20210909_1328'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lineitem',
            name='video',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='projectvideos', to='FileCollector.projectvideo'),
        ),
    ]
