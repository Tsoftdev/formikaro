# Generated by Django 3.1.5 on 2021-03-02 13:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FormikoBot', '0019_auto_20210302_1208'),
    ]

    operations = [
        migrations.AddField(
            model_name='assettype',
            name='name',
            field=models.CharField(default=1, max_length=10),
            preserve_default=False,
        ),
    ]
