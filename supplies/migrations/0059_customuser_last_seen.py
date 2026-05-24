from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0058_appsettings_home_table_display'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='last_seen',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
