# Generated by Django 2.0.3 on 2018-11-14 22:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consorcios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='consorcio',
            name='costo_mp',
            field=models.BooleanField(default=False),
        ),
    ]
