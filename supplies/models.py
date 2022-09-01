import datetime

from django.db import models
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField


class CustomUser(AbstractUser):
    pass
    np_contact_sender_ref = models.CharField(max_length=100, null=True)
    mobNumber = models.CharField(max_length=100, null=True)
    np_sender_ref = models.CharField(max_length=100, null=True)
    np_last_choosed_delivery_place_id = models.SmallIntegerField(blank=True, null=True)

    def __str__(self):
        return self.username

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


class CreateParselModel(models.Model):

    class PaymentUserType(models.TextChoices):
        ВІДПРАВНИК = "Sender"
        ОТРИМУВАЧ = "Recipient"

    class PaymentMoneyType(models.TextChoices):
        БЕЗГОТІВКОВИЙ = "NonCash"
        ГОТІВКА = "Cash"

    payment_user_type = models.CharField(choices=PaymentUserType.choices, max_length=12, default=PaymentUserType.ВІДПРАВНИК)
    payment_money_type = models.CharField(choices=PaymentMoneyType.choices, max_length=12, default=PaymentMoneyType.БЕЗГОТІВКОВИЙ)
    sender_np_place = models.ForeignKey(SenderNPPlaceInfo, on_delete=models.SET_NULL, null=True)
    width = models.PositiveIntegerField()
    length = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    weight = models.PositiveIntegerField()
    seatsAmount = models.PositiveIntegerField()
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

    def __str__(self):
        return f'{self.id} - {self.name}'

    class Meta:
        verbose_name = 'Товар (назва)'
        verbose_name_plural = 'Товари (назва)'


class Supply(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    general_supply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True, related_name='general')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    ref = models.CharField(max_length=50, null=True, blank=True)
    supplyLot = models.CharField(max_length=50, null=True, blank=True)
    count = models.PositiveIntegerField(null=True, blank=True)
    countOnHold = models.PositiveIntegerField(null=True, blank=True, default=0)
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


    def __str__(self):
        return f'{self.id} - {self.general_supply.name}'

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'





class Place(models.Model):
    name = models.CharField(max_length=200)
    city_ref = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=100, null=True, blank=True)
    link = models.CharField(max_length=300, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    organization_code = models.PositiveIntegerField(null=True, blank=True)
    ref_NP = models.CharField(max_length=100, null=True, blank=True)
    worker_NP = models.OneToOneField('Workers', on_delete=models.SET_NULL, null=True, blank=True)
    address_NP = models.OneToOneField('DeliveryPlace', on_delete=models.SET_NULL, null=True, blank=True, unique=True)
    isAddedToNP = models.BooleanField(default=False, blank=True)
    name_in_NP = models.CharField(max_length=200, null=True, blank=True)


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
        return f'{self.name} {self.secondName}, працює в {self.for_place.name}, {self.for_place.city}'

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


class Order(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)
    documentsId = ArrayField(models.CharField(max_length=200), blank=True, null=True)


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


class NPDeliveryCreatedDetailInfo(models.Model):
    document_id = models.CharField(max_length=50)
    ref = models.CharField(max_length=50)
    cost_on_site = models.PositiveIntegerField()
    estimated_time_delivery = models.CharField(max_length=12)
    for_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)

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



class PreOrder(models.Model):
    userCreated = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f'презаказ № {self.id}, для {self.place.name}, от {self.dateSent}'

    class Meta:
        verbose_name = 'Передзамовлення'
        verbose_name_plural = 'Передзамовлення'


class SupplyInPreorder(models.Model):
    count_in_order = models.PositiveIntegerField(null=True, blank=True)
    generalSupply = models.ForeignKey(GeneralSupply, on_delete=models.SET_NULL, null=True, blank=True)
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True)
    supply_for_order = models.ForeignKey(PreOrder, on_delete=models.CASCADE, null=True)
    lot = models.CharField(max_length=20, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True, blank=True)

    def __str__(self):
        name = None
        if self.generalSupply:
            name = self.generalSupply.name
        elif self.supply:
            name = self.supply.general_supply.name

        return f'ID order: {self.supply_for_order.id} | name: {name}'

    class Meta:
        verbose_name = 'Товар в Передзамовленні'
        verbose_name_plural = 'Товари в Передзамовленнях'



class SupplyInOrder(models.Model):
    count_in_order = models.PositiveIntegerField(null=True, blank=True)
    generalSupply = models.ForeignKey(GeneralSupply, on_delete=models.SET_NULL, null=True, blank=True, related_name='inGeneralSupp')
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True, related_name='inSupply')
    supply_for_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    lot = models.CharField(max_length=20, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True, blank=True)
    internalName = models.CharField(max_length=50, null=True, blank=True)
    internalRef = models.CharField(max_length=30, null=True, blank=True)


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
    in_city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'{self.general_device.name} in {self.in_place.name}, {self.in_place.city_ref.name}'

    class Meta:
        verbose_name = 'Прилад'
        verbose_name_plural = 'Прилади'