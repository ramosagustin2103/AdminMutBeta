# Generated by Django 2.0.3 on 2018-12-06 23:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0005_auto_20181206_1230'),
    ]

    operations = [
        migrations.AddField(
            model_name='cierre',
            name='mails',
            field=models.BooleanField(default=False),
        ),
    ]
