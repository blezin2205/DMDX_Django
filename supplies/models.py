from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth.signals import user_logged_in


def user_logged_in_handler(sender, request, user, **kwargs):
    UserSession.objects.get_or_create(user=user, session_id=request.session.session_key)


class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True)


def get_last_name(self):
    return self.last_name

User.add_to_class("__str__", get_last_name)


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
    name = models.CharField(max_length=50, null=True)
    ref = models.CharField(max_length=20, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)


    def isInPreorderCart(self):
        return SupplyInPreorderInCart.objects.filter(general_supply_id=self.id).exists()

    def __str__(self):
        return f'{self.id} - {self.name}'

    class Meta:
        verbose_name = 'Товар (назва)'
        verbose_name_plural = 'Товари (назва)'


class Supply(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    general_supply = models.ForeignKey(GeneralSupply, on_delete=models.CASCADE, null=True, related_name='general')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    ref = models.CharField(max_length=20, null=True, blank=True)
    supplyLot = models.CharField(max_length=20, null=True, blank=True)
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
        return SupplyInOrderInCart.objects.filter(supply_id=self.id).exists()

    def isInPreorderCart(self):
        userObj = UserSession.objects.first()
        return SupplyInPreorderInCart.objects.filter(supply_id=self.id, supply_for_order__userCreated=userObj.user).exists()

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
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.name}, {self.city_ref.name}'

    class Meta:
        verbose_name = 'Організація'
        verbose_name_plural = 'Організації'


class Workers(models.Model):
    name = models.CharField(max_length=50)
    telNumber = models.CharField(max_length=20)
    position = models.CharField(max_length=20)
    for_place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'{self.name}, працює в {self.for_place.name}, {self.for_place.city}'

    class Meta:
        verbose_name = 'Працівник'
        verbose_name_plural = 'Працівники'


class ServiceNote(models.Model):
    id = models.AutoField(primary_key=True)
    description = models.TextField(null=True)
    dateCreated = models.DateField(null=True, blank=True, auto_now_add=True)
    for_place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    from_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f' №{self.id}, {self.for_place.name}, {self.for_place.city}'

    class Meta:
        verbose_name = 'Сервісна замітка'
        verbose_name_plural = 'Сервісні замітки'


class Order(models.Model):
    userCreated = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f'Заказ № {self.id}, для {self.place.name}, от {self.dateSent}'

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'


class PreOrder(models.Model):
    userCreated = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
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
    userCreated = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
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
    userCreated = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
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