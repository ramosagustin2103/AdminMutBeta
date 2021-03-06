# Generated by Django 2.0.3 on 2018-10-30 14:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('consorcios', '0001_initial'),
        ('comprobantes', '0002_auto_20181030_1145'),
        ('afip', '0003_auto_20180821_1213'),
        ('mp', '0018_auto_20180808_1242'),
        ('arquitectura', '0002_auto_20181030_1145'),
        ('creditos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='compensacion',
            name='credito_destino',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='creditos.Credito'),
        ),
        migrations.AddField(
            model_name='compensacion',
            name='punto',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='afip.PointOfSales'),
        ),
        migrations.AddField(
            model_name='compensacion',
            name='socio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arquitectura.Socio'),
        ),
        migrations.AddField(
            model_name='cobro',
            name='compensacion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='comprobantes.Compensacion'),
        ),
        migrations.AddField(
            model_name='cobro',
            name='comprobante',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='comprobantes.Comprobante'),
        ),
        migrations.AddField(
            model_name='cobro',
            name='consorcio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='consorcios.Consorcio'),
        ),
        migrations.AddField(
            model_name='cobro',
            name='credito',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='creditos.Credito'),
        ),
        migrations.AddField(
            model_name='cobro',
            name='mercado_pago',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='mp.Payment'),
        ),
        migrations.AddField(
            model_name='cobro',
            name='socio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='arquitectura.Socio'),
        ),
        migrations.AddField(
            model_name='cajacomprobante',
            name='caja',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='arquitectura.Caja'),
        ),
        migrations.AddField(
            model_name='cajacomprobante',
            name='comprobante',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comprobantes.Comprobante'),
        ),
    ]
