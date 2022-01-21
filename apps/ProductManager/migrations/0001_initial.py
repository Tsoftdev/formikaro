# Generated by Django 3.1.5 on 2021-03-11 14:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('FormikoBot', '0001_initial'),
        ('FileCollector', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('abbreviation', models.CharField(max_length=10, unique=True)),
                ('name', models.CharField(max_length=256)),
            ],
            options={
                'db_table': 'fo_language',
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fsin', models.CharField(blank=True, max_length=30, null=True, unique=True)),
                ('is_active', models.BooleanField(default=False)),
                ('price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('variety', models.CharField(blank=True, default='', max_length=4)),
                ('version', models.IntegerField(default='1')),
                ('comment', models.TextField(blank=True)),
                ('vimeo_id', models.CharField(blank=True, max_length=10)),
                ('runtime', models.IntegerField(default='0')),
                ('rendertime', models.IntegerField(default='0')),
                ('change_log', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'fo_product',
            },
        ),
        migrations.CreateModel(
            name='Resolution',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('width', models.IntegerField(default='1280')),
                ('height', models.IntegerField(default='720')),
                ('quality', models.IntegerField(default='2')),
                ('name', models.CharField(max_length=25)),
                ('description', models.TextField()),
            ],
            options={
                'db_table': 'fo_resolution',
            },
        ),
        migrations.CreateModel(
            name='ProductTextModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('desc_short', models.TextField()),
                ('desc_long', models.TextField()),
                ('default', models.BooleanField(blank=True, default=False)),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ProductManager.language')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_texts', to='ProductManager.product')),
            ],
            options={
                'db_table': 'fo_product_text',
            },
        ),
        migrations.CreateModel(
            name='ProductBase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fsin_base', models.CharField(blank=True, max_length=10, null=True, unique=True)),
                ('mode', models.CharField(choices=[('AE', 'After Effects'), ('PR', 'Premiere'), ('FO', 'FormikoBot')], default='AE', max_length=8)),
                ('name', models.CharField(max_length=30)),
                ('needs_intake', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('assets', models.ManyToManyField(blank=True, related_name='product_assets', to='FormikoBot.Asset')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='FileCollector.projectmanager')),
            ],
            options={
                'db_table': 'fo_product_base',
            },
        ),
        migrations.AddField(
            model_name='product',
            name='base',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ProductManager.productbase'),
        ),
        migrations.AddField(
            model_name='product',
            name='language',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ProductManager.language'),
        ),
        migrations.AddField(
            model_name='product',
            name='resolution',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ProductManager.resolution'),
        ),
    ]
