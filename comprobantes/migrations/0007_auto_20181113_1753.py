# Generated by Django 2.0.3 on 2018-11-13 20:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comprobantes', '0006_auto_20181112_1336'),
    ]

    operations = [
        migrations.AddField(
            model_name='cajacomprobante',
            name='anulacion',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='cobro',
            name='anulacion',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='saldo',
            name='anulacion',
            field=models.BooleanField(default=False),
        ),
    ]
