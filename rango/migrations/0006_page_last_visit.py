# Generated by Django 3.2.6 on 2021-08-30 09:35

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('rango', '0005_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='last_visit',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
