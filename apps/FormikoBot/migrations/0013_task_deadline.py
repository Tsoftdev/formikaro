# Generated by Django 3.1.5 on 2021-09-17 09:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FormikoBot', '0012_task_unitprice'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='deadline',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
