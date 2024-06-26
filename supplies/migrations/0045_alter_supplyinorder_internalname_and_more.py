# Generated by Django 4.0.4 on 2024-01-09 23:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0044_deliveryorder_ishasbeensaved_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplyinorder',
            name='internalName',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='supplyinorder',
            name='internalRef',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='supplyinorder',
            name='lot',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.CreateModel(
            name='SupplyInBookedOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_in_order', models.PositiveIntegerField(blank=True, null=True)),
                ('lot', models.CharField(blank=True, max_length=100, null=True)),
                ('date_expired', models.DateField(null=True)),
                ('date_created', models.DateField(blank=True, null=True)),
                ('internalName', models.CharField(blank=True, max_length=500, null=True)),
                ('internalRef', models.CharField(blank=True, max_length=100, null=True)),
                ('generalSupply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.generalsupply')),
                ('supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.supply')),
            ],
            options={
                'verbose_name': 'Товар в бронюванні',
                'verbose_name_plural': 'Товари в бронюванні',
            },
        ),
    ]
