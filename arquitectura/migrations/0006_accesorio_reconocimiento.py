# Generated by Django 2.0.3 on 2018-11-26 12:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arquitectura', '0005_grupo_baja'),
    ]

    operations = [
        migrations.AddField(
            model_name='accesorio',
            name='reconocimiento',
            field=models.IntegerField(choices=[(1, 'Diario'), (7, 'Semanal'), (15, 'Quincenal'), (30, 'Mensual'), (60, 'Bimestral'), (90, 'Trimestral'), (120, 'Semestral')], default=1),
        ),
    ]
