# Generated by Django 2.0.3 on 2018-11-01 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('creditos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='factura',
            name='observacion',
            field=models.TextField(blank=True, null=True),
        ),
    ]
