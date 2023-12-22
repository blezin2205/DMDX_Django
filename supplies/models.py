import datetime

from django.db import models
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.postgres.fields import ArrayField
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files import File
from django.db.models import Q
from django.db.models import Count, Sum
from cloudinary import uploader
from cloudinary.models import CloudinaryField
from django import forms
import cloudinary
from django.core.serializers import serialize
from django.http import JsonResponse
from django.forms.models import model_to_dict
import json

class CustomUser(AbstractUser):
    pass
    np_contact_sender_ref = models.CharField(max_length=100, null=True)
    mobNumber = models.CharField(max_length=100, null=True)
    np_sender_ref = models.CharField(max_length=100, null=True)
    np_last_choosed_delivery_place_id = models.SmallIntegerField(blank=True, null=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class SenderNPPlaceInfo(models.Model):
    cityName = models.CharField(max_length=200, blank=True)
    addressName = models.CharField(max_length=200, blank=True)
    city_ref_NP = models.CharField(max_length=100, blank=True)
    address_ref_NP = models.CharField(max_length=100, blank=True)
    deliveryType = models.CharField(max_length=20, blank=True)
    for_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, related_name='sender_np_places')

    def __str__(self):
        return f'{self.cityName}, {self.addressName}'

    class Meta:
        verbose_name = 'Місце відправки НП'
        verbose_name_plural = 'Місця відправок НП'


class RegisterNPInfo(models.Model):
    barcode_string = models.CharField(max_length=200)
    register_url = models.CharField(max_length=800, blank=True)
    barcode = models.ImageField(upload_to='images/', blank=True)
    barcode_url = models.CharField(max_length=800, blank=True, null=True)
    date = models.CharField(max_length=200)
    register_ref = models.CharField(max_length=100, blank=True)
    documentsId = ArrayField(models.CharField(max_length=400), blank=True, null=True)
    for_orders = ArrayField(models.CharField(max_length=400), blank=True, null=True)

    def __str__(self):
        return str(self.barcode_string)

    def save(self, *args, **kwargs):
        EAN = barcode.get_barcode_class('code128')
        ean = EAN(f'{self.barcode_string}', writer=ImageWriter())
        buffer = BytesIO()
        ean.write(buffer)
        self.barcode.save(f'{self.barcode_string}.png', File(buffer), save=False)
        uploader.upload(self.barcode, public_id=f'{self.barcode_string}', unique_filename=False, overwrite=True,
                        folder='register_np_barcodes')
        srcURL = cloudinary.CloudinaryImage(f'register_np_barcodes/{self.barcode_string}').build_url()
        self.barcode_url = srcURL
        return super().save(*args, **kwargs)


class CreateParselModel(models.Model):
    class PaymentUserType(models.TextChoices):
        ВІДПРАВНИК = "Sender"
        ОТРИМУВАЧ = "Recipient"

    class PaymentMoneyType(models.TextChoices):
        БЕЗГОТІВКОВИЙ = "NonCash"
        ГОТІВКА = "Cash"

    payment_user_type = models.CharField(choices=PaymentUserType.choices, max_length=12,
                                         default=PaymentUserType.ВІДПРАВНИК)
    payment_money_type = models.CharField(choices=PaymentMoneyType.choices, max_length=12,
                                          default=PaymentMoneyType.БЕЗГОТІВКОВИЙ)
    sender_np_place = models.ForeignKey(SenderNPPlaceInfo, on_delete=models.SET_NULL, null=True)
    width = models.PositiveIntegerField()
    length = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    weight = models.PositiveIntegerField()
    seatsAmount = models.PositiveIntegerField(default=1)
    description = models.CharField(max_length=200, default="Товари медичного призначення")
    cost = models.PositiveIntegerField(null=True, blank=True, default=300)
    dateDelivery = models.DateField(auto_now_add=True)


class City(models.Model):
    name = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Місто'
        verbose_name_plural = 'Міста'


class Category(models.Model):
    name = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'


class GeneralSupply(models.Model):
    name = models.CharField(max_length=200, null=True)
    ref = models.CharField(max_length=50, null=True, blank=True)
    SMN_code = models.CharField(max_length=50, null=True, blank=True)
    package_and_tests = models.CharField(max_length=50, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    image = CloudinaryField("Image", overwrite=True, resource_type="image", transformation={"quality": "auto:eco"},
                            format="jpg", null=True, default=None, blank=True, folder='general_supply_media')

    def __str__(self):
        try:
            name = self.name
        except:
            name = "NO NAME"

        return name

    def to_json(self):
        general_supply_dict = model_to_dict(self)
        serialized = json.dumps(general_supply_dict)

        # Deserialize the JSON to a Python object (optional)
        # deserialized_data = json.loads(json_data)
        return serialized

    class Meta:
        verbose_name = 'Товар (назва)'
        verbose_name_plural = 'Товари (назва)'


class SupplySaveFromScanApiModel(models.Model):
    smn = models.CharField(max_length=50, null=True, blank=True)
    supplyLot = models.CharField(max_length=50, null=True, blank=True)
    expiredDate = models.DateField(null=True)
    count = models.PositiveIntegerField(null=True, blank=True)


class Supply(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300, null=True, blank=True)
    general_supply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True, related_name='general')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    ref = models.CharField(max_length=50, null=True, blank=True)
    supplyLot = models.CharField(max_length=50, null=True, blank=True)
    count = models.PositiveIntegerField(null=True, blank=True)
    countOnHold = models.PositiveIntegerField(null=True, blank=True, default=0)
    preCountOnHold = models.PositiveIntegerField(null=True, blank=True, default=0)
    dateCreated = models.DateField(null=True, auto_now_add=True)
    expiredDate = models.DateField(null=True)

    def date_is_good(self):
        return self.expiredDate > timezone.now().date()

    def date_is_expired(self):
        return self.expiredDate < timezone.now().date()

    def date_is_today(self):
        return self.expiredDate == timezone.now().date()

    def isInCart(self):
        return SupplyInOrderInCart.objects.get(supply_id=self.id).exists()

    def getTotalOnHold(self):
        return self.countOnHold + self.preCountOnHold

    def availableCount(self):
        return self.count - self.getTotalOnHold()

    def get_supp_for_history(self):
        return SupplyForHistory(name=self.name,
                                general_supply=self.general_supply,
                                category=self.category,
                                ref=self.ref,
                                supplyLot=self.supplyLot,
                                count=self.count,
                                dateCreated=timezone.now().date(),
                                expiredDate=self.expiredDate)

    def __str__(self):
        name = "No name"
        try:
            name = self.general_supply.name
        except:
            pass
        return name

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'


from django.db.models import Q


class Place(models.Model):
    name = models.CharField(max_length=200)
    city_ref = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=100, null=True, blank=True)
    link = models.CharField(max_length=300, null=True, blank=True)
    user = models.ManyToManyField(CustomUser, blank=True)
    allowed_categories = models.ManyToManyField(Category, blank=True)
    organization_code = models.CharField(max_length=10, null=True, blank=True)
    ref_NP = models.CharField(max_length=100, null=True, blank=True)
    worker_NP = models.OneToOneField('Workers', on_delete=models.SET_NULL, null=True, blank=True)
    address_NP = models.OneToOneField('DeliveryPlace', on_delete=models.SET_NULL, null=True, blank=True, unique=True)
    isAddedToNP = models.BooleanField(default=False, blank=True)
    isPrivatePlace = models.BooleanField(default=False, blank=True)
    name_in_NP = models.CharField(max_length=200, null=True, blank=True)

    def isHaveUncompletedPreorders(self):
        if self.preorder_set.exists():
            if self.preorder_set.filter(state_of_delivery='Awaiting').exists() or self.preorder_set.filter(
                    state_of_delivery='Partial').exists():
                return True
            else:
                return False
        else:
            return False

    def getUcompletePreorderSet(self):
        return self.preorder_set.filter(Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial'))

    def __str__(self):
        return f'{self.name}, {self.city_ref.name}'

    class Meta:
        verbose_name = 'Організація'
        verbose_name_plural = 'Організації'


class DeliveryPlace(models.Model):
    cityName = models.CharField(max_length=200, blank=True)
    addressName = models.CharField(max_length=200, blank=True)
    city_ref_NP = models.CharField(max_length=100, blank=True)
    address_ref_NP = models.CharField(max_length=100, blank=True)
    deliveryType = models.CharField(max_length=20, blank=True)
    for_place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True, related_name='delivery_places')

    def __str__(self):
        return f'{self.cityName}, {self.addressName}'

    class Meta:
        verbose_name = 'Місце доставки НП'
        verbose_name_plural = 'Місця доставок для організацій НП'


class Workers(models.Model):
    name = models.CharField(max_length=100)
    secondName = models.CharField(max_length=100, null=True)
    middleName = models.CharField(max_length=100, null=True, blank=True)
    telNumber = models.CharField(max_length=12, default='38')
    position = models.CharField(max_length=100, null=True, blank=True)
    for_place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True, related_name='workers')
    ref_NP = models.CharField(max_length=100, null=True, blank=True)
    ref_counterparty_NP = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        user_np_type = None
        try:
            telNumber = self.telNumber
            counterpartyRef = self.ref_counterparty_NP
            if counterpartyRef is not None and counterpartyRef == '3b13350b-2a6b-11eb-8513-b88303659df5':
                user_np_type = ', (Приватна особа)'
            elif counterpartyRef is not None:
                user_np_type = ', (Організація)'
        except:
            user_np_type = ''
            telNumber = ''
        return f'{self.name} {self.secondName}{user_np_type} {telNumber}'

    class Meta:
        verbose_name = 'Працівник'
        verbose_name_plural = 'Працівники'


class ServiceNote(models.Model):
    id = models.AutoField(primary_key=True)
    description = models.TextField(null=True)
    dateCreated = models.DateField(null=True, blank=True, auto_now_add=True)
    for_place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    from_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f' №{self.id}, {self.for_place.name}, {self.for_place.city}'

    class Meta:
        verbose_name = 'Сервісна замітка'
        verbose_name_plural = 'Сервісні замітки'


class Agreement(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    description = models.CharField(max_length=300, null=True, blank=True)
    for_place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f'{self.id}, {self.description}'

    class Meta:
        verbose_name = 'Договір'
        verbose_name_plural = 'Договори'


class PreOrder(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    isPreorder = models.BooleanField(default=False, blank=True)
    comment = models.CharField(max_length=300, null=True, blank=True)
    dateToOrdered = models.DateField(null=True, blank=True)
    isClosed = models.BooleanField(default=False)

    STATE_CHOICES = (
        ('awaiting_from_customer', 'Формується замовником'),
        ('accepted_by_customer', 'Підтверджено замовником'),
        ('Awaiting', 'Замовлено у виробника'),
        ('Partial', 'Частково поставлено'),
        ('Complete', 'Повністю поставлено'),
    )
    state_of_delivery = models.CharField(max_length=50, choices=STATE_CHOICES, default='awaiting_from_customer')

    def __str__(self):
        return f'презаказ № {self.id}, для {self.place.name}, от {self.dateSent}'

    def get_state_of_delivery_value(self):
        return self.get_state_of_delivery_display()

    def checkIfUncompletedDeliveryPreordersExist(self):
        return PreOrder.objects.filter(Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial')).exists()

    class Meta:
        verbose_name = 'Передзамовлення'
        verbose_name_plural = 'Передзамовлення'


class BookedOrder(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    for_preorder = models.ForeignKey(PreOrder, on_delete=models.SET_NULL, null=True, blank=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    isComplete = models.BooleanField(default=False)
    isPreorder = models.BooleanField(default=False, blank=True)
    comment = models.CharField(max_length=300, null=True, blank=True)

    STATE_CHOICES = (
        ('Awaiting', 'Створено'),
        ('Partial', 'Частково поставлено'),
        ('Complete', 'Повністю поставлено'),
    )
    state_of_delivery = models.CharField(max_length=50, choices=STATE_CHOICES, default='Awaiting')

    def __str__(self):
        return f'Бронь № {self.id}, для {self.place.name}, от {self.dateCreated}'

    def get_state_of_delivery_value(self):
        return self.get_state_of_delivery_display()

    def checkIfUncompletedDeliveryPreordersExist(self):
        return PreOrder.objects.filter(Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial')).exists()

    class Meta:
        verbose_name = 'Бронювання'
        verbose_name_plural = 'Бронювання'


class Order(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    for_preorder = models.ForeignKey(PreOrder, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='orders_for_preorder')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)
    documentsId = ArrayField(models.CharField(max_length=200), blank=True, null=True)
    for_agreement = models.ForeignKey(Agreement, on_delete=models.SET_NULL, null=True, blank=True)
    dateToSend = models.DateField(null=True, blank=True)

    def get_np_DocumetsIdList(self):
        set = self.npdeliverycreateddetailinfo_set.all()
        list = []
        for obj in set:
            list.append({"DocumentNumber": obj.document_id})
        return list

    def get_parsel_delivery_status(self):
        return int(self.statusnpparselfromdoucmentid_set.first().status_code)

    def __str__(self):
        return f'Заказ № {self.id}, для {self.place.name}, от {self.dateSent}'

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'


class SupplyForHistory(models.Model):
    name = models.CharField(max_length=300, null=True, blank=True)
    history_description = models.CharField(max_length=500, null=True, blank=True)
    general_supply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True)
    supply_for_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    ref = models.CharField(max_length=50, null=True, blank=True)
    supplyLot = models.CharField(max_length=50, null=True, blank=True)
    count = models.PositiveIntegerField(null=True, blank=True)
    dateCreated = models.DateField(null=True, auto_now_add=True)
    expiredDate = models.DateField(null=True)

    ACTION_TYPE = (
        ('added-handle', 'Додано(Вручну)'),
        ('added-scan', 'Додано(Скан)'),
        ('added-order', 'Додано в замовлення'),
        ('deleted', 'Видалено'),
        ('updated', 'Оновлено'),
    )
    action_type = models.CharField(max_length=100, choices=ACTION_TYPE, blank=True, null=True)

    def get_action_type_value(self):
        return self.get_action_type_display()

    def get_sup_id_in_order_if_exist(self):
        try:
            order = self.supply_for_order
            supsInOrder = order.supplyinorder_set.get(lot=self.supplyLot,
                                                      date_expired=self.expiredDate)
            return supsInOrder.id
        except:
            return 0

    def __str__(self):
        return self.general_supply.name

    class Meta:
        verbose_name = 'Товар (Історія)'
        verbose_name_plural = 'Товари (Історія)'


class NPDeliveryCreatedDetailInfo(models.Model):
    document_id = models.CharField(max_length=50)
    ref = models.CharField(max_length=50)
    cost_on_site = models.PositiveIntegerField()
    estimated_time_delivery = models.CharField(max_length=12)
    recipient_worker = models.CharField(max_length=200, null=True, blank=True)
    recipient_address = models.CharField(max_length=200, null=True, blank=True)
    for_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'Накладна № {self.document_id}, для замовлення №{self.for_order.id}'

    class Meta:
        verbose_name = 'НП Інфо по накладним'
        verbose_name_plural = 'НП Накладні'


class StatusNPParselFromDoucmentID(models.Model):
    status_code = models.CharField(max_length=50)
    status_desc = models.CharField(max_length=200)
    docNumber = models.CharField(max_length=50)
    for_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    counterpartyRecipientDescription = models.CharField(max_length=50, blank=True, null=True)
    documentWeight = models.CharField(max_length=50, blank=True, null=True)
    factualWeight = models.CharField(max_length=50, blank=True, null=True)
    payerType = models.CharField(max_length=50, blank=True, null=True)
    seatsAmount = models.CharField(max_length=50, blank=True, null=True)
    phoneRecipient = models.CharField(max_length=50, blank=True, null=True)
    scheduledDeliveryDate = models.CharField(max_length=50, blank=True, null=True)
    documentCost = models.CharField(max_length=50, blank=True, null=True)
    paymentMethod = models.CharField(max_length=50, blank=True, null=True)
    warehouseSender = models.CharField(max_length=300, blank=True, null=True)
    dateCreated = models.CharField(max_length=50, blank=True, null=True)
    dateScan = models.CharField(max_length=50, blank=True, null=True)
    actualDeliveryDate = models.CharField(max_length=50, blank=True, null=True)
    recipientDateTime = models.CharField(max_length=50, blank=True, null=True)
    recipientAddress = models.CharField(max_length=300, blank=True, null=True)
    recipientFullNameEW = models.CharField(max_length=300, blank=True, null=True)
    cargoDescriptionString = models.CharField(max_length=300, blank=True, null=True)
    announcedPrice = models.CharField(max_length=50, blank=True, null=True)


class SupplyInAgreement(models.Model):
    count_in_agreement = models.PositiveIntegerField(null=True, blank=True)
    generalSupply = models.ForeignKey(GeneralSupply, on_delete=models.SET_NULL, null=True, blank=True)
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True)
    supply_for_agreement = models.ForeignKey(Agreement, on_delete=models.CASCADE, null=True)
    lot = models.CharField(max_length=20, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True, blank=True)

    def __str__(self):
        name = None
        if self.generalSupply:
            name = self.generalSupply.name
        elif self.supply:
            name = self.supply.general_supply.name

        return f'ID Agreement: {self.supply_for_agreement.id} | name: {name}'

    class Meta:
        verbose_name = 'Товар в Договорі'
        verbose_name_plural = 'Товари в Договорах'

    def getAlreadyDeliveredCount(self):
        count = 0
        orders = self.supply_for_agreement.order_set.all()
        for order in orders:
            print(order.id)
            gen_sup = order.supplyinorder_set.filter(generalSupply=self.generalSupply)
            print(gen_sup)
            counties = gen_sup.aggregate(total_count=Sum('count_in_order'))
            try:
                total_count = counties["total_count"]
                print(f'Total count --------------  {total_count}')
                count += total_count
            except:
                print(f'Total count --------------  {count}')

        return count

    def supIsFullyDelivered(self):
        print(f'getAlreadyDeliveredCount  --- {self.getAlreadyDeliveredCount()}')
        print(f'count_in_agreement -----  {self.count_in_agreement}')
        return self.getAlreadyDeliveredCount() == self.count_in_agreement


class SupplyInPreorder(models.Model):
    count_in_order = models.PositiveIntegerField(null=True, blank=True)
    count_in_order_current = models.PositiveIntegerField(default=0)
    generalSupply = models.ForeignKey(GeneralSupply, on_delete=models.SET_NULL, null=True, blank=True)
    supply_for_order = models.ForeignKey(PreOrder, on_delete=models.CASCADE, null=True)
    STATE_CHOICES = (
        ('Awaiting', 'Очікується'),
        ('Partial', 'Частково поставлено'),
        ('Complete', 'Повністю поставлено'),
    )
    state_of_delivery = models.CharField(max_length=20, choices=STATE_CHOICES, default='Awaiting')

    def __str__(self):
        name = None
        if self.generalSupply:
            name = self.generalSupply.name

        return f'ID order: {self.supply_for_order.id} | name: {name}'

    class Meta:
        verbose_name = 'Товар в Передзамовленні'
        verbose_name_plural = 'Товари в Передзамовленнях'


class SupplyInBookedOrder(models.Model):
    count_in_order = models.PositiveIntegerField(null=True, blank=True)
    generalSupply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True, blank=True)
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, null=True, blank=True)
    supply_in_booked_order = models.ForeignKey(BookedOrder, on_delete=models.CASCADE, null=True, blank=True)
    lot = models.CharField(max_length=100, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True, blank=True)
    internalName = models.CharField(max_length=500, null=True, blank=True)
    internalRef = models.CharField(max_length=100, null=True, blank=True)

    def date_is_good(self):
        return self.date_expired > self.supply_in_booked_order.dateCreated

    def date_is_expired(self):
        return self.date_expired < self.supply_in_booked_order.dateCreated

    def date_is_today(self):
        return self.date_expired == self.supply_in_booked_order.dateCreated

    def hasSupply(self):
        return self.supply.inSupply.exists()

    def __str__(self):
        try:
            orderId = self.supply_in_booked_order.id
        except:
            orderId = 'No ID'

        try:
            name = self.generalSupply.name
        except:
            name = 'No Name'

        try:
            supname = self.supply.name
        except:
            supname = 'No Name'

        return f'ID order: {orderId} | name: {name}'

    class Meta:
        verbose_name = 'Товар в бронюванні'
        verbose_name_plural = 'Товари в бронюванні'


class SupplyInOrder(models.Model):
    count_in_order = models.PositiveIntegerField(null=True, blank=True)
    generalSupply = models.ForeignKey(GeneralSupply, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='inGeneralSupp')
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True, related_name='inSupply')
    supply_in_preorder = models.ForeignKey(SupplyInPreorder, on_delete=models.SET_NULL, null=True, blank=True)
    supply_for_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    lot = models.CharField(max_length=100, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True, blank=True)
    internalName = models.CharField(max_length=500, null=True, blank=True)
    internalRef = models.CharField(max_length=100, null=True, blank=True)

    def date_is_good(self):
        return self.date_expired > self.supply_for_order.dateCreated

    def date_is_expired(self):
        return self.date_expired < self.supply_for_order.dateCreated

    def date_is_today(self):
        return self.date_expired == self.supply_for_order.dateCreated

    def hasSupply(self):
        return self.supply.inSupply.exists()

    def __str__(self):
        try:
            orderId = self.supply_for_order.id
        except:
            orderId = 'No ID'

        try:
            name = self.generalSupply.name
        except:
            name = 'No Name'

        try:
            supname = self.supply.name
        except:
            supname = 'No Name'

        return f'ID order: {orderId} | name: {name}'

    class Meta:
        verbose_name = 'Товар в замовленні'
        verbose_name_plural = 'Товари в замовленнях'


class OrderInCart(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f'Заказ № {self.id}'

    class Meta:
        verbose_name = 'Замовлення в корзині'
        verbose_name_plural = 'Замовлення в корзині'

    @property
    def get_cart_items(self):
        orderitems = self.supplyinorderincart_set.all()
        total = sum([item.count_in_order for item in orderitems])
        return total


class SupplyInOrderInCart(models.Model):
    count_in_order = models.PositiveIntegerField(null=True, blank=True, default=0)
    supply = models.OneToOneField(Supply, on_delete=models.SET_NULL, null=True, blank=True)
    supply_for_order = models.ForeignKey(OrderInCart, on_delete=models.CASCADE, null=True)
    lot = models.CharField(max_length=20, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'Товар: для замовлення в коризні '

    class Meta:
        verbose_name = 'Товар в замовленні в корзині'
        verbose_name_plural = 'Товари в замовленні в коризні'


class PreorderInCart(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f'передЗаказ № {self.id}'

    class Meta:
        verbose_name = 'передЗамовлення в корзині'
        verbose_name_plural = 'передЗамовлення в корзині'

    @property
    def get_cart_items(self):
        orderitems = self.supplyinpreorderincart_set.all()
        total = sum([item.count_in_order for item in orderitems])
        return total


class SupplyInPreorderInCart(models.Model):
    count_in_order = models.PositiveIntegerField(null=True, blank=True, default=0)
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True)
    supply_for_order = models.ForeignKey(PreorderInCart, on_delete=models.CASCADE, null=True)
    lot = models.CharField(max_length=20, null=True, blank=True)
    date_expired = models.DateField(null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    general_supply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f'Товар: для передзамовлення в коризні '

    class Meta:
        verbose_name = 'Товар в передзамовленні в корзині'
        verbose_name_plural = 'Товари в передзамовленні в коризні'


class GeneralDevice(models.Model):
    name = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Прилад (назва)'
        verbose_name_plural = 'Прилади (назва)'


class Device(models.Model):
    general_device = models.ForeignKey(GeneralDevice, on_delete=models.CASCADE, null=True)
    serial_number = models.CharField(max_length=50, null=True, blank=True)
    in_place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    date_installed = models.DateField(null=True, blank=True)
    image = CloudinaryField("Image", overwrite=True, resource_type="image", transformation={"quality": "auto:eco"},
                            format="jpg", null=True, default=None, blank=True, folder='device_media')
    in_city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'{self.id}'

    class Meta:
        verbose_name = 'Прилад'
        verbose_name_plural = 'Прилади'


class DeliveryOrder(models.Model):
    date_created = models.DateField(null=True, blank=True, auto_now_add=True)
    comment = models.TextField(null=True, blank=True)
    from_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    isHasBeenSaved = models.BooleanField(default=False)


class DeliverySupplyInCart(models.Model):
    barcode = models.CharField(max_length=300, null=True, blank=True)
    SMN_code = models.CharField(max_length=300, null=True, blank=True)
    general_supply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True)
    supplyLot = models.CharField(max_length=50, null=True, blank=True)
    count = models.PositiveIntegerField(null=True, blank=True)
    expiredDate_desc = models.CharField(max_length=50, null=True, blank=True)
    expiredDate = models.DateField(null=True, blank=True)
    isRecognized = models.BooleanField(default=False)
    isHandleAdded = models.BooleanField(default=False)
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True)
    delivery_order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, null=True)

    def date_is_good(self):
        return self.expiredDate > self.delivery_order.date_created

    def date_is_expired(self):
        return self.expiredDate < self.delivery_order.date_created

    def date_is_today(self):
        return self.expiredDate == self.delivery_order.date_created

    def __str__(self):
        return f'{self.general_supply}'

    class Meta:
        verbose_name = 'Додані товари з поставки'
        verbose_name_plural = 'Додані товари з поставки'



