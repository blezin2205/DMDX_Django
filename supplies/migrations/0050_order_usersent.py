# Generated by Django 4.2.4 on 2025-03-18 20:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0049_alter_bookedsupplyinorderincart_lot_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='userSent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_orders', to=settings.AUTH_USER_MODEL),
        ),
    ]
