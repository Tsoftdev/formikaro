# Generated by Django 3.1.4 on 2021-01-28 20:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('FileCollector', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkStep',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=15)),
                ('desc', models.CharField(max_length=100)),
                ('json', models.JSONField(blank=True, default=list, null=True)),
                ('description', models.TextField(blank=True)),
                ('mode', models.CharField(choices=[('MAN', 'MANUAL'), ('FO', 'FormikoBot')], default='MAN', max_length=8)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'fo_workstep',
            },
        ),
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=50, null=True)),
                ('value', models.CharField(blank=True, max_length=30, null=True, unique=True)),
                ('type', models.CharField(choices=[('PNG', 'PNG Graphic (.png)'), ('JPG', 'JPEG Graphic (.jpg)'), ('VEC', 'Vector Graphic (.ai)'), ('MOV', 'Video (.mov)'), ('HEX', 'Color (Code RGB)')], default='', max_length=8)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_file', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('client_owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_owned_assets', to='FileCollector.client')),
                ('company_owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='company_owned_assets', to='FileCollector.company')),
            ],
            options={
                'db_table': 'fo_asset',
            },
        ),
    ]
