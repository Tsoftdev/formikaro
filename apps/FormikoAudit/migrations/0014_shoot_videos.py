# Generated by Django 3.1.5 on 2021-11-25 14:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0044_merge_20211005_2103'),
        ('FormikoAudit', '0013_auto_20211124_2102'),
    ]

    operations = [
        migrations.AddField(
            model_name='shoot',
            name='videos',
            field=models.ManyToManyField(related_name='shoot_videos', to='FileCollector.ProjectVideo'),
        ),
    ]
