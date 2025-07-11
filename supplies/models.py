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
from django.forms import ModelForm, Form
from .NPModels import *
import json
from googletrans import Translator


class CustomUser(AbstractUser):
    pass
    np_contact_sender_ref = models.CharField(max_length=100, null=True)
    mobNumber = models.CharField(max_length=100, null=True)
    np_sender_ref = models.CharField(max_length=100, null=True)
    np_last_choosed_delivery_place_id = models.SmallIntegerField(blank=True, null=True)
    
    def isAllowToEditAndCreateActions(self):
        return self.is_admin() or self.is_engineer() or self.is_staff or self.is_superuser

    def get_user_place_id(self):
        try:
            place_id = Place.objects.get(user=self).id
        except:
            place_id = "NO EXIST"
        return place_id

    def isClient(self):
        return self.groups.filter(name='client').exists()

    def is_employee(self):
        return self.groups.filter(name='empl').exists()

    def is_admin(self):
        return self.groups.filter(name='admin').exists()

    def is_engineer(self):
        return self.groups.filter(name='engineer').exists()

    def get_role(self):
        if self.is_admin():
            return 'admin'
        elif self.is_employee():
            return 'empl'
        elif self.is_client():
            return 'client'
        elif self.is_engineer():
            return 'engineer'
        return None

    def get_app_settings(self):
        app_settings, created = AppSettings.objects.get_or_create(userCreated=self)
        return app_settings
    
    def is_allow_to_edit_preorder(self):
        return self.get_app_settings().enable_preorder_editing_awaiting_state and self.isAllowToEditAndCreateActions()

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class AppSettings(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    send_teams_msg = models.BooleanField(default=True)
    send_teams_msg_preorders = models.BooleanField(default=True)
    enable_show_other_booked_cart = models.BooleanField(default=False)
    disable_order_confirmation_send_action = models.BooleanField(default=False)
    enable_preorder_editing_awaiting_state = models.BooleanField(default=False)

    def __str__(self):
        return self.userCreated


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
    cargo_type = models.CharField(
        choices=CargoType.choices(),
        max_length=20,
        default=CargoType.PARCEL.value
    )
    width = models.PositiveIntegerField()
    length = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    weight = models.PositiveIntegerField()
    seatsAmount = models.PositiveIntegerField(default=1)
    description = models.CharField(max_length=200, default="Товари медичного призначення")
    cost = models.PositiveIntegerField(null=True, blank=True, default=300)
    dateDelivery = models.DateField(auto_now_add=True)

    @property
    def cargo_type_display(self):
        return self.get_cargo_type_display()


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
    name = models.CharField(max_length=500, null=True)
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
    name = models.CharField(max_length=500, null=True, blank=True)
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

    def get_place_name(self):
        return f'{self.name}, {self.city_ref.name}'

    def get_place_name_en(self):
        """
        Get place name translated to English
        """
        try:
            translator = Translator()
            translated = translator.translate(self.name, src='uk', dest='en')
            return translated.text
        except Exception:
            # If translation fails, return original name
            return self.name

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
            if counterpartyRef is not None and counterpartyRef == settings.NOVA_POSHTA_SENDER_DMDX_REF_PRIVATE_COUNTERAGENT:
                user_np_type = ', (Приватна особа)'
            elif counterpartyRef is not None:
                user_np_type = ', (Організація)'
        except:
            user_np_type = ''
            telNumber = ''
        return f'{self.name} {self.secondName}{user_np_type} {telNumber}'

    def get_full_name(self):
        full_name = self.name
        if self.middleName:
            full_name += " " + self.middleName
        if self.secondName:
            full_name += " " + self.secondName

        return full_name

    def get_np_status(self):
        counterpartyRef = self.ref_counterparty_NP
        user_np_type = None
        if counterpartyRef is not None and counterpartyRef == settings.NOVA_POSHTA_SENDER_DMDX_REF_PRIVATE_COUNTERAGENT:
            user_np_type = 'Приватна особа'
        elif counterpartyRef is not None:
            user_np_type = 'Організація'
        return user_np_type

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



class PreOrder(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    isPinned = models.BooleanField(default=False)
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
        ('Complete_Handle', 'Повністю поставлено(Закрито вручну)'),
    )
    state_of_delivery = models.CharField(max_length=50, choices=STATE_CHOICES, default='awaiting_from_customer')
    
    def checkIfCartSupsExistInSelf(self):
        """
        Check if any supplies from the cart exist in this preorder.
        
        Args:
            sups_in_cart: List of Supply objects to check
            
        Returns:
            bool: True if any of the supplies exist in the preorder, False otherwise
        """
        try:
            orderInCart = OrderInCart.objects.first()
            sups_in_cart = orderInCart.supplyinorderincart_set.all()
            general_sups = [sup.supply.general_supply for sup in sups_in_cart]
            preorder_sups = self.supplyinpreorder_set.all()
            
            # Check if any of the cart supplies exist in the preorder
            for cart_sup in general_sups:
                if preorder_sups.filter(generalSupply=cart_sup).exists():
                    return True
        except:
            return False
        
        # Check if any of the cart supplies exist in the preorder
        for cart_sup in general_sups:
            if preorder_sups.filter(generalSupply=cart_sup).exists():
                return True
                
        return False

    def __str__(self):
        return f'презаказ № {self.id}, для {self.place.name}, от {self.dateSent}'

    def get_state_of_delivery_value(self):
        return self.get_state_of_delivery_display()

    def checkIfUncompletedDeliveryPreordersExist(self):
        return PreOrder.objects.filter(Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial')).exists()
    
    def checkIfUncompletedPreordersExist(self):
        return PreOrder.objects.filter(Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial') | Q(state_of_delivery='accepted_by_customer')).exists()

    def isAvailableToEdit(self):
        return (self.state_of_delivery == 'awaiting_from_customer' or self.state_of_delivery == 'accepted_by_customer')

    def update_order_state_of_delivery_status(self):
        """Updates the state_of_delivery based on the status of supplies in the preorder"""
        sups_in_preorder = self.supplyinpreorder_set.all()
        if all(sp.state_of_delivery == 'Complete' for sp in sups_in_preorder):
            self.state_of_delivery = 'Complete'
        elif any(sp.state_of_delivery in ['Partial', 'Awaiting'] for sp in sups_in_preorder):
            self.state_of_delivery = 'Partial'
        self.save(update_fields=['state_of_delivery'])

    class Meta:
        verbose_name = 'Передзамовлення'
        verbose_name_plural = 'Передзамовлення'


# class BookedOrder(models.Model):
#     userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
#     for_preorder = models.ForeignKey(PreOrder, on_delete=models.SET_NULL, null=True, blank=True)
#     place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
#     dateCreated = models.DateField(auto_now_add=True, null=True)
#     isComplete = models.BooleanField(default=False)
#     isPreorder = models.BooleanField(default=False, blank=True)
#     comment = models.CharField(max_length=300, null=True, blank=True)
#
#     STATE_CHOICES = (
#         ('Awaiting', 'Створено'),
#         ('Partial', 'Частково поставлено'),
#         ('Complete', 'Повністю поставлено'),
#     )
#     state_of_delivery = models.CharField(max_length=50, choices=STATE_CHOICES, default='Awaiting')
#
#     def __str__(self):
#         return f'Бронь № {self.id}, для {self.place.name}, от {self.dateCreated}'
#
#     def get_state_of_delivery_value(self):
#         return self.get_state_of_delivery_display()
#
#     def checkIfUncompletedDeliveryPreordersExist(self):
#         return PreOrder.objects.filter(Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial')).exists()
#
#     class Meta:
#         verbose_name = 'Бронювання'
#         verbose_name_plural = 'Бронювання'


class Order(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    userSent = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='sent_orders')
    for_preorder = models.ForeignKey(PreOrder, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='orders_for_preorder')
    related_preorders = models.ManyToManyField(PreOrder, blank=True, related_name='related_orders')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    isPinned = models.BooleanField(default=False)
    isMerged = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)
    documentsId = ArrayField(models.CharField(max_length=200), blank=True, null=True)
    dateToSend = models.DateField(null=True, blank=True)
    
    def date_send_is_good(self):
        return self.dateToSend > timezone.now().date()

    def date_send_is_expired(self):
        return self.dateToSend < timezone.now().date()

    def date_send_is_today(self):
        return self.dateToSend == timezone.now().date()

    def isForPreorderOrItemHasPreorder(self):
        return self.supplyinorder_set.filter(supply_in_preorder__isnull=False)

    def get_np_DocumetsIdList(self):
        set = self.npdeliverycreateddetailinfo_set.all()
        list = []
        for obj in set:
            list.append({"DocumentNumber": obj.document_id})
        return list

    def get_parsel_delivery_status(self):
        return int(self.statusnpparselfromdoucmentid_set.first().status_code)

    def isClientCreated(self):
        return self.userCreated.isClient()
    
    def isUncompletedPreorderForPlaceExist(self):
        return self.place.preorder_set.filter(Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial') | Q(state_of_delivery='accepted_by_customer')).exists()
    
    def add_preorder_to_related(self, preorder):
        if self.for_preorder:
            self.related_preorders.add(self.for_preorder)
            self.for_preorder = None
            self.save(update_fields=['for_preorder'])
        self.related_preorders.add(preorder)   

    def __str__(self):
        return f'Заказ № {self.id}, для {self.place.name}, от {self.dateSent}'

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'


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
    counterpartyRecipientDescription = models.CharField(max_length=500, blank=True, null=True)
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

    def get_booked_count(self):
        sups_booked_count = self.supplyinbookedorder_set.all().aggregate(total_count=Sum('count_in_order'))[
            "total_count"]
        if sups_booked_count:
            return sups_booked_count
        else:
            return 0

    def check_if_in_sup_in_rder_exist_booked_sup(self):
        return self.supplyinorder_set.filter(supply_in_booked_order__isnull=False).exists()

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
    countOnHold = models.PositiveIntegerField(null=True, blank=True, default=0)
    generalSupply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True, blank=True)
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, null=True, blank=True)
    supply_for_place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True, blank=True)
    supply_in_preorder = models.ForeignKey(SupplyInPreorder, on_delete=models.SET_NULL, null=True, blank=True)
    lot = models.CharField(max_length=100, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True, blank=True)
    internalName = models.CharField(max_length=500, null=True, blank=True)
    internalRef = models.CharField(max_length=100, null=True, blank=True)

    @property
    def get_sub_el_with_in_cart(self):
        count_in_order_in_cart = 0
        try:
            sups_in_cart = BookedSupplyInOrderInCart.objects.get(supply=self)
            count_in_order_in_cart = sups_in_cart.count_in_order
        except:
            pass
        cond = self.count_in_order - self.countOnHold - count_in_order_in_cart
        return cond <= 0

    def hasSupply(self):
        return self.supply.inSupply.exists()

    def __str__(self):
        try:
            orderId = self.id
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
    supply_in_booked_order = models.ForeignKey(SupplyInBookedOrder, on_delete=models.SET_NULL, null=True, blank=True)
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

    def check_if_has_plus_button(self):
        if self.supply_in_booked_order:
            available = self.supply_in_booked_order.count_in_order - self.supply_in_booked_order.countOnHold
            return available > 0
        else:
            return self.supply.count - self.supply.countOnHold > 0

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
    lot = models.CharField(max_length=50, null=True, blank=True)
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
    lot = models.CharField(max_length=50, null=True, blank=True)
    date_expired = models.DateField(null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    general_supply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f'Товар: для передзамовлення в коризні '

    class Meta:
        verbose_name = 'Товар в передзамовленні в корзині'
        verbose_name_plural = 'Товари в передзамовленні в коризні'


class BookedOrderInCart(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f'Заказ № {self.id}'

    class Meta:
        verbose_name = 'Бронювання в корзині'
        verbose_name_plural = 'Бронювання в корзині'

    @property
    def get_cart_items(self):
        orderitems = self.bookedsupplyinorderincart_set.all()
        total = sum([item.count_in_order for item in orderitems])
        return total

    def has_uncomplete_orders(self):
        return self.place.order_set.filter(isComplete=False).exists()


class BookedSupplyInOrderInCart(models.Model):
    count_in_order = models.PositiveIntegerField(null=True, blank=True, default=0)
    supply = models.OneToOneField(SupplyInBookedOrder, on_delete=models.CASCADE, null=True, blank=True)
    supply_for_order = models.ForeignKey(BookedOrderInCart, on_delete=models.CASCADE, null=True)
    lot = models.CharField(max_length=50, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'Товар: для Бронюванні в коризні '

    def date_is_good(self):
        return self.date_expired > timezone.now().date()

    def date_is_expired(self):
        return self.date_expired < timezone.now().date()

    def date_is_today(self):
        return self.date_expired == timezone.now().date()

    class Meta:
        verbose_name = 'Товар в Бронюванні в корзині'
        verbose_name_plural = 'Товари в Бронюванні в коризні'


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
