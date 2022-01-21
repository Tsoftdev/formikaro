# Generated by Django 3.1.6 on 2021-05-24 14:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FormikoBot', '0003_task'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(choices=[('OP', 'OPEN'), ('AC', 'ACTIVE'), ('FD', 'FAILED'), ('CM', 'COMPLETE')], default='OPEN', max_length=8),
        ),
    ]
