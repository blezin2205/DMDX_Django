from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0060_remove_appsettings_send_teams_msg_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='isDocumentsRequired',
            field=models.BooleanField(blank=True, default=True),
        ),
    ]
