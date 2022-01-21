# Generated by Django 3.1.6 on 2021-02-26 20:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('FormikoBot', '0007_auto_20210226_2130'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetPreset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=30)),
                ('description', models.TextField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('assettype', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='FormikoBot.assettype')),
            ],
        ),
    ]