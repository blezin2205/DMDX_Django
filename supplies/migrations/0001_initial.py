# Generated by Django 4.0.4 on 2022-09-22 19:38

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('np_contact_sender_ref', models.CharField(max_length=100, null=True)),
                ('mobNumber', models.CharField(max_length=100, null=True)),
                ('np_sender_ref', models.CharField(max_length=100, null=True)),
                ('np_last_choosed_delivery_place_id', models.SmallIntegerField(blank=True, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, null=True)),
            ],
            options={
                'verbose_name': 'Категорія',
                'verbose_name_plural': 'Категорії',
            },
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, null=True)),
            ],
            options={
                'verbose_name': 'Місто',
                'verbose_name_plural': 'Міста',
            },
        ),
        migrations.CreateModel(
            name='DeliveryPlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cityName', models.CharField(blank=True, max_length=200)),
                ('addressName', models.CharField(blank=True, max_length=200)),
                ('city_ref_NP', models.CharField(blank=True, max_length=100)),
                ('address_ref_NP', models.CharField(blank=True, max_length=100)),
                ('deliveryType', models.CharField(blank=True, max_length=20)),
            ],
            options={
                'verbose_name': 'Місце доставки НП',
                'verbose_name_plural': 'Місця доставок для організацій НП',
            },
        ),
        migrations.CreateModel(
            name='GeneralDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, null=True)),
            ],
            options={
                'verbose_name': 'Прилад (назва)',
                'verbose_name_plural': 'Прилади (назва)',
            },
        ),
        migrations.CreateModel(
            name='GeneralSupply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, null=True)),
                ('ref', models.CharField(blank=True, max_length=50, null=True)),
                ('SMN_code', models.CharField(blank=True, max_length=50, null=True)),
                ('package_and_tests', models.CharField(blank=True, max_length=50, null=True)),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.category')),
            ],
            options={
                'verbose_name': 'Товар (назва)',
                'verbose_name_plural': 'Товари (назва)',
            },
        ),
        migrations.CreateModel(
            name='NPCity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, null=True)),
                ('ref', models.CharField(max_length=100, null=True)),
                ('area', models.CharField(max_length=100, null=True)),
                ('settlementType', models.CharField(max_length=100, null=True)),
                ('cityID', models.CharField(max_length=100, null=True)),
                ('settlementTypeDescription', models.CharField(max_length=100, null=True)),
                ('areaDescription', models.CharField(max_length=100, null=True)),
            ],
            options={
                'verbose_name': 'Нова Пошта - Місто',
                'verbose_name_plural': 'Нова Пошта - Міста',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dateCreated', models.DateField(auto_now_add=True, null=True)),
                ('dateSent', models.DateField(blank=True, null=True)),
                ('isComplete', models.BooleanField(default=False)),
                ('comment', models.CharField(blank=True, max_length=300, null=True)),
                ('documentsId', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, null=True, size=None)),
            ],
            options={
                'verbose_name': 'Замовлення',
                'verbose_name_plural': 'Замовлення',
            },
        ),
        migrations.CreateModel(
            name='OrderInCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dateCreated', models.DateField(auto_now_add=True, null=True)),
                ('dateSent', models.DateField(blank=True, null=True)),
                ('isComplete', models.BooleanField(default=False)),
                ('comment', models.CharField(blank=True, max_length=300, null=True)),
            ],
            options={
                'verbose_name': 'Замовлення в корзині',
                'verbose_name_plural': 'Замовлення в корзині',
            },
        ),
        migrations.CreateModel(
            name='Place',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('address', models.CharField(blank=True, max_length=100, null=True)),
                ('link', models.CharField(blank=True, max_length=300, null=True)),
                ('organization_code', models.CharField(blank=True, max_length=8, null=True)),
                ('ref_NP', models.CharField(blank=True, max_length=100, null=True)),
                ('isAddedToNP', models.BooleanField(blank=True, default=False)),
                ('name_in_NP', models.CharField(blank=True, max_length=200, null=True)),
                ('address_NP', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.deliveryplace')),
                ('city_ref', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.city')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Організація',
                'verbose_name_plural': 'Організації',
            },
        ),
        migrations.CreateModel(
            name='PreOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dateCreated', models.DateField(auto_now_add=True, null=True)),
                ('dateSent', models.DateField(blank=True, null=True)),
                ('isComplete', models.BooleanField(default=False)),
                ('comment', models.CharField(blank=True, max_length=300, null=True)),
                ('place', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.place')),
                ('userCreated', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Передзамовлення',
                'verbose_name_plural': 'Передзамовлення',
            },
        ),
        migrations.CreateModel(
            name='PreorderInCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dateCreated', models.DateField(auto_now_add=True, null=True)),
                ('dateSent', models.DateField(blank=True, null=True)),
                ('isComplete', models.BooleanField(default=False)),
                ('comment', models.CharField(blank=True, max_length=300, null=True)),
                ('place', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.place')),
                ('userCreated', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'передЗамовлення в корзині',
                'verbose_name_plural': 'передЗамовлення в корзині',
            },
        ),
        migrations.CreateModel(
            name='RegisterNPInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('barcode_string', models.CharField(max_length=200)),
                ('register_url', models.CharField(blank=True, max_length=800)),
                ('barcode', models.ImageField(blank=True, upload_to='images/')),
                ('date', models.CharField(max_length=200)),
                ('register_ref', models.CharField(blank=True, max_length=100)),
                ('documentsId', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=400), blank=True, null=True, size=None)),
                ('for_orders', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=400), blank=True, null=True, size=None)),
            ],
        ),
        migrations.CreateModel(
            name='Supply',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('ref', models.CharField(blank=True, max_length=50, null=True)),
                ('supplyLot', models.CharField(blank=True, max_length=50, null=True)),
                ('count', models.PositiveIntegerField(blank=True, null=True)),
                ('countOnHold', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('dateCreated', models.DateField(auto_now_add=True, null=True)),
                ('expiredDate', models.DateField(null=True)),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.category')),
                ('general_supply', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='general', to='supplies.generalsupply')),
            ],
            options={
                'verbose_name': 'Товар',
                'verbose_name_plural': 'Товари',
            },
        ),
        migrations.CreateModel(
            name='SupplySaveFromScanApiModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('smn', models.CharField(blank=True, max_length=50, null=True)),
                ('supplyLot', models.CharField(blank=True, max_length=50, null=True)),
                ('expiredDate', models.DateField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Workers',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('secondName', models.CharField(max_length=100, null=True)),
                ('middleName', models.CharField(blank=True, max_length=100, null=True)),
                ('telNumber', models.CharField(default='38', max_length=12)),
                ('position', models.CharField(blank=True, max_length=100, null=True)),
                ('ref_NP', models.CharField(blank=True, max_length=100, null=True)),
                ('ref_counterparty_NP', models.CharField(blank=True, max_length=100, null=True)),
                ('for_place', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workers', to='supplies.place')),
            ],
            options={
                'verbose_name': 'Працівник',
                'verbose_name_plural': 'Працівники',
            },
        ),
        migrations.CreateModel(
            name='SupplyInPreorderInCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_in_order', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('lot', models.CharField(blank=True, max_length=20, null=True)),
                ('date_expired', models.DateField(blank=True, null=True)),
                ('date_created', models.DateField(blank=True, null=True)),
                ('general_supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.generalsupply')),
                ('supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.supply')),
                ('supply_for_order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.preorderincart')),
            ],
            options={
                'verbose_name': 'Товар в передзамовленні в корзині',
                'verbose_name_plural': 'Товари в передзамовленні в коризні',
            },
        ),
        migrations.CreateModel(
            name='SupplyInPreorder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_in_order', models.PositiveIntegerField(blank=True, null=True)),
                ('lot', models.CharField(blank=True, max_length=20, null=True)),
                ('date_expired', models.DateField(null=True)),
                ('date_created', models.DateField(blank=True, null=True)),
                ('generalSupply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.generalsupply')),
                ('supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.supply')),
                ('supply_for_order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.preorder')),
            ],
            options={
                'verbose_name': 'Товар в Передзамовленні',
                'verbose_name_plural': 'Товари в Передзамовленнях',
            },
        ),
        migrations.CreateModel(
            name='SupplyInOrderInCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_in_order', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('lot', models.CharField(blank=True, max_length=20, null=True)),
                ('date_expired', models.DateField(null=True)),
                ('date_created', models.DateField(blank=True, null=True)),
                ('supply', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.supply')),
                ('supply_for_order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.orderincart')),
            ],
            options={
                'verbose_name': 'Товар в замовленні в корзині',
                'verbose_name_plural': 'Товари в замовленні в коризні',
            },
        ),
        migrations.CreateModel(
            name='SupplyInOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_in_order', models.PositiveIntegerField(blank=True, null=True)),
                ('lot', models.CharField(blank=True, max_length=20, null=True)),
                ('date_expired', models.DateField(null=True)),
                ('date_created', models.DateField(blank=True, null=True)),
                ('internalName', models.CharField(blank=True, max_length=50, null=True)),
                ('internalRef', models.CharField(blank=True, max_length=30, null=True)),
                ('generalSupply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inGeneralSupp', to='supplies.generalsupply')),
                ('supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inSupply', to='supplies.supply')),
                ('supply_for_order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.order')),
            ],
            options={
                'verbose_name': 'Товар в замовленні',
                'verbose_name_plural': 'Товари в замовленнях',
            },
        ),
        migrations.CreateModel(
            name='StatusNPParselFromDoucmentID',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status_code', models.CharField(max_length=50)),
                ('status_desc', models.CharField(max_length=200)),
                ('docNumber', models.CharField(max_length=50)),
                ('counterpartyRecipientDescription', models.CharField(blank=True, max_length=50)),
                ('documentWeight', models.CharField(blank=True, max_length=50)),
                ('factualWeight', models.CharField(blank=True, max_length=50)),
                ('payerType', models.CharField(blank=True, max_length=50)),
                ('seatsAmount', models.CharField(blank=True, max_length=50)),
                ('phoneRecipient', models.CharField(blank=True, max_length=50)),
                ('scheduledDeliveryDate', models.CharField(blank=True, max_length=50)),
                ('documentCost', models.CharField(blank=True, max_length=50)),
                ('paymentMethod', models.CharField(blank=True, max_length=50)),
                ('warehouseSender', models.CharField(blank=True, max_length=300)),
                ('dateCreated', models.DateTimeField(blank=True, default=None)),
                ('dateScan', models.DateTimeField(blank=True, default=None)),
                ('recipientAddress', models.CharField(blank=True, max_length=300)),
                ('recipientFullNameEW', models.CharField(blank=True, max_length=300)),
                ('cargoDescriptionString', models.CharField(blank=True, max_length=300)),
                ('announcedPrice', models.CharField(blank=True, max_length=50)),
                ('for_order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.order')),
            ],
        ),
        migrations.CreateModel(
            name='ServiceNote',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('description', models.TextField(null=True)),
                ('dateCreated', models.DateField(auto_now_add=True, null=True)),
                ('for_place', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.place')),
                ('from_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Сервісна замітка',
                'verbose_name_plural': 'Сервісні замітки',
            },
        ),
        migrations.CreateModel(
            name='SenderNPPlaceInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cityName', models.CharField(blank=True, max_length=200)),
                ('addressName', models.CharField(blank=True, max_length=200)),
                ('city_ref_NP', models.CharField(blank=True, max_length=100)),
                ('address_ref_NP', models.CharField(blank=True, max_length=100)),
                ('deliveryType', models.CharField(blank=True, max_length=20)),
                ('for_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sender_np_places', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Місце відправки НП',
                'verbose_name_plural': 'Місця відправок НП',
            },
        ),
        migrations.AddField(
            model_name='place',
            name='worker_NP',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.workers'),
        ),
        migrations.AddField(
            model_name='orderincart',
            name='place',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.place'),
        ),
        migrations.AddField(
            model_name='orderincart',
            name='userCreated',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='order',
            name='place',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.place'),
        ),
        migrations.AddField(
            model_name='order',
            name='userCreated',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='NPDeliveryCreatedDetailInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_id', models.CharField(max_length=50)),
                ('ref', models.CharField(max_length=50)),
                ('cost_on_site', models.PositiveIntegerField()),
                ('estimated_time_delivery', models.CharField(max_length=12)),
                ('recipient_worker', models.CharField(blank=True, max_length=200, null=True)),
                ('recipient_address', models.CharField(blank=True, max_length=200, null=True)),
                ('for_order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.order')),
            ],
            options={
                'verbose_name': 'НП Інфо по накладним',
                'verbose_name_plural': 'НП Накладні',
            },
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial_number', models.CharField(blank=True, max_length=50, null=True)),
                ('date_installed', models.DateField(blank=True, null=True)),
                ('general_device', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.generaldevice')),
                ('in_city', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.city')),
                ('in_place', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='supplies.place')),
            ],
            options={
                'verbose_name': 'Прилад',
                'verbose_name_plural': 'Прилади',
            },
        ),
        migrations.AddField(
            model_name='deliveryplace',
            name='for_place',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='delivery_places', to='supplies.place'),
        ),
        migrations.CreateModel(
            name='CreateParselModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_user_type', models.CharField(choices=[('Sender', 'Відправник'), ('Recipient', 'Отримувач')], default='Sender', max_length=12)),
                ('payment_money_type', models.CharField(choices=[('NonCash', 'Безготівковий'), ('Cash', 'Готівка')], default='NonCash', max_length=12)),
                ('width', models.PositiveIntegerField()),
                ('length', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField()),
                ('weight', models.PositiveIntegerField()),
                ('seatsAmount', models.PositiveIntegerField(default=1)),
                ('description', models.CharField(default='Товари медичного призначення', max_length=200)),
                ('cost', models.PositiveIntegerField(blank=True, default=300, null=True)),
                ('dateDelivery', models.DateField(auto_now_add=True)),
                ('sender_np_place', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='supplies.sendernpplaceinfo')),
            ],
        ),
    ]
