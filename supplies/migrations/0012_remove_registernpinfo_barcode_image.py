# Generated by Django 4.0.4 on 2023-01-10 16:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0011_registernpinfo_barcode_image'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='registernpinfo',
            name='barcode_image',
        ),
    ]