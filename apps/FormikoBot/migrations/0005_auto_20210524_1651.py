# Generated by Django 3.1.6 on 2021-05-24 14:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0023_video_size'),
        ('FormikoBot', '0004_auto_20210524_1642'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='creator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_tasks', to='FileCollector.projectmanager'),
        ),
        migrations.AlterField(
            model_name='task',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='FileCollector.projectmanager'),
        ),
    ]
