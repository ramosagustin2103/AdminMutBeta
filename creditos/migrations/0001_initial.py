# Generated by Django 2.0.3 on 2018-10-30 14:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('consorcios', '0001_initial'),
        ('afip', '0003_auto_20180821_1213'),
        ('contabilidad', '0001_initial'),
        ('arquitectura', '0002_auto_20181030_1145'),
    ]

    operations = [
        migrations.CreateModel(
            name='Credito',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(blank=True, null=True)),
                ('periodo', models.DateField(blank=True, null=True)),
                ('vencimiento', models.DateField(blank=True, null=True)),
                ('gracia', models.DateField(blank=True, null=True)),
                ('capital', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('fin', models.DateField(blank=True, null=True)),
                ('acc_desc', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='acc_desc', to='arquitectura.Accesorio')),
                ('acc_int', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='acc_int', to='arquitectura.Accesorio')),
                ('accesorios', models.ManyToManyField(blank=True, to='arquitectura.Accesorio')),
                ('consorcio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='consorcios.Consorcio')),
                ('dominio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='arquitectura.Dominio')),
            ],
        ),
        migrations.CreateModel(
            name='Factura',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf', models.FileField(blank=True, null=True, upload_to='liquidaciones/pdf/')),
                ('consorcio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='consorcios.Consorcio')),
            ],
        ),
        migrations.CreateModel(
            name='Liquidacion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveIntegerField(blank=True, null=True)),
                ('fecha', models.DateField(blank=True, null=True)),
                ('capital', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('estado', models.CharField(choices=[('en_proceso', 'En proceso'), ('errores', 'Errores'), ('confirmado', 'Confirmado')], max_length=15)),
                ('asiento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contabilidad.Asiento')),
                ('consorcio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='consorcios.Consorcio')),
                ('punto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='afip.PointOfSales')),
            ],
        ),
        migrations.CreateModel(
            name='Mail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('liquidacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='creditos.Liquidacion')),
                ('socio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='arquitectura.Socio')),
            ],
        ),
        migrations.CreateModel(
            name='PdfSocio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf', models.FileField(upload_to='liquidaciones/pdf/')),
                ('liquidacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='creditos.Liquidacion')),
                ('socio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='arquitectura.Socio')),
            ],
        ),
        migrations.AddField(
            model_name='factura',
            name='liquidacion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='creditos.Liquidacion'),
        ),
        migrations.AddField(
            model_name='factura',
            name='receipt',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='afip.Receipt'),
        ),
        migrations.AddField(
            model_name='factura',
            name='socio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='arquitectura.Socio'),
        ),
        migrations.AddField(
            model_name='credito',
            name='factura',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='creditos.Factura'),
        ),
        migrations.AddField(
            model_name='credito',
            name='ingreso',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='arquitectura.Ingreso'),
        ),
        migrations.AddField(
            model_name='credito',
            name='liquidacion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='creditos.Liquidacion'),
        ),
        migrations.AddField(
            model_name='credito',
            name='padre',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hijos', to='creditos.Credito'),
        ),
        migrations.AddField(
            model_name='credito',
            name='socio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='arquitectura.Socio'),
        ),
    ]