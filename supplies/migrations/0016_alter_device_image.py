# Generated by Django 4.0.4 on 2023-01-10 21:32

import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0015_registernpinfo_barcode_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='image',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, verbose_name='Image'),
        ),
    ]