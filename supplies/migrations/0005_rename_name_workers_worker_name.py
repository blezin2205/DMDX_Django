# Generated by Django 4.0.4 on 2022-05-12 20:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0004_alter_place_address_alter_place_city_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='workers',
            old_name='name',
            new_name='worker_name',
        ),
    ]