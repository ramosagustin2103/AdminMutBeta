# Generated by Django 2.0.3 on 2019-01-09 23:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0001_initial'),
        ('consorcios', '0002_consorcio_costo_mp'),
        ('arquitectura', '0007_auto_20181130_1243'),
        ('afip', '0003_auto_20180821_1213'),
        ('herramientas', '0002_bienvenida_saludo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transferencia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(blank=True, null=True)),
                ('numero', models.PositiveIntegerField(blank=True, null=True)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('valor', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('pdf', models.FileField(blank=True, null=True, upload_to='compensacion/pdf/')),
                ('asiento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contabilidad.Asiento')),
                ('caja_destino', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transferencia_destino', to='arquitectura.Caja')),
                ('caja_origen', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transferencia_origen', to='arquitectura.Caja')),
                ('consorcio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='consorcios.Consorcio')),
                ('punto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='afip.PointOfSales')),
            ],
        ),
    ]
