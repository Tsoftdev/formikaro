# Generated by Django 3.1.5 on 2021-05-05 10:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('FileCollector', '0015_video_episode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intake',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='FileCollector.order'),
        ),
    ]
