# Generated by Django 4.0.4 on 2022-12-06 17:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0008_supply_precountonhold'),
    ]

    operations = [
        migrations.CreateModel(
            name='Agreement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=300, null=True)),
                ('dateCreated', models.DateField(auto_now_add=True, null=True)),
                ('isComplete', models.BooleanField(default=False)),
                ('comment', models.CharField(blank=True, max_length=300, null=True)),
                ('for_place', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.place')),
                ('userCreated', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Договір',
                'verbose_name_plural': 'Договори',
            },
        ),
        migrations.CreateModel(
            name='SupplyInAgreement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_in_agreement', models.PositiveIntegerField(blank=True, null=True)),
                ('lot', models.CharField(blank=True, max_length=20, null=True)),
                ('date_expired', models.DateField(null=True)),
                ('date_created', models.DateField(blank=True, null=True)),
                ('generalSupply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.generalsupply')),
                ('supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.supply')),
                ('supply_for_agreement', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.agreement')),
            ],
            options={
                'verbose_name': 'Товар в Договорі',
                'verbose_name_plural': 'Товари в Договорах',
            },
        ),
        migrations.AddField(
            model_name='order',
            name='for_agreement',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.agreement'),
        ),
    ]