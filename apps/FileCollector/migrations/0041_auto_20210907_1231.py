# Generated by Django 3.1.5 on 2021-09-07 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0040_auto_20210907_1229'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectvideo',
            name='discount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='projectvideo',
            name='unitprice',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='projectvideo',
            name='videos',
            field=models.ManyToManyField(null=True, related_name='project_videos', to='FileCollector.Video'),
        ),
    ]
