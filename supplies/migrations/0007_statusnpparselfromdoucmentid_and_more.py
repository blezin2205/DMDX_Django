# Generated by Django 4.0.4 on 2022-08-30 00:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0006_createparselmodel_npdeliverycreateddetailinfo'),
    ]

    operations = [
        migrations.CreateModel(
            name='StatusNPParselFromDoucmentID',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status_code', models.CharField(max_length=50)),
                ('status_desc', models.CharField(max_length=200)),
                ('docNumber', models.CharField(max_length=50)),
            ],
        ),
        migrations.AlterField(
            model_name='deliveryplace',
            name='for_place',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='delivery_places', to='supplies.place'),
        ),
        migrations.AlterField(
            model_name='place',
            name='address_NP',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.deliveryplace'),
        ),
    ]