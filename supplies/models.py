from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from django.utils.html import format_html

from DMDX_Django import settings

def get_last_name(self):
    return self.last_name

User.add_to_class("__str__", get_last_name)


class Category(models.Model):
    name = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'


class Supply(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    ref = models.CharField(max_length=20, null=True, blank=True)
    supplyLot = models.CharField(max_length=20, null=True, blank=True)
    count = models.PositiveIntegerField(null=True, blank=True)
    countOnHold = models.PositiveIntegerField(null=True, blank=True)
    dateCreated = models.DateField(null=True, auto_created=True)
    expiredDate = models.DateField(null=True)

    def date_is_good(self):
        return self.expiredDate > timezone.now().date()

    def date_is_expired(self):
        return self.expiredDate < timezone.now().date()

    def date_is_today(self):
        return self.expiredDate == timezone.now().date()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'


class Place(models.Model):
    name = models.CharField(max_length=30)
    city = models.CharField(max_length=20)
    address = models.CharField(max_length=50, null=True, blank=True)
    link = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f'{self.name}, {self.city}'

    class Meta:
        verbose_name = 'Організація'
        verbose_name_plural = 'Організації'


class Workers(models.Model):
    name = models.CharField(max_length=50)
    telNumber = models.CharField(max_length=20)
    position = models.CharField(max_length=20)
    for_place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.name}, працює в {self.for_place.name}, {self.for_place.city}'

    class Meta:
        verbose_name = 'Працівник'
        verbose_name_plural = 'Працівники'


class ServiceNote(models.Model):
    id = models.AutoField(primary_key=True)
    description = models.TextField(null=True)
    dateCreated = models.DateField(null=True, blank=True, auto_now_add=True)
    for_place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True)
    from_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f' №{self.id}, {self.for_place.name}, {self.for_place.city}'

    class Meta:
        verbose_name = 'Сервісна замітка'
        verbose_name_plural = 'Сервісні замітки'


class Order(models.Model):
    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True)
    dateCreated = models.DateField(auto_now_add=True, null=True)
    dateSent = models.DateField(null=True, blank=True)
    isComplete = models.BooleanField(default=False)
    comment = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f'Заказ № {self.id}, для {self.place.name}, {self.place.city} от {self.dateSent}'

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'


class SupplyInOrder(models.Model):
    id = models.AutoField(primary_key=True)
    count_in_order = models.PositiveIntegerField(null=True, blank=True)
    supply_in_storage = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True)
    supply_for = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, related_name='supplies')
    lot = models.CharField(max_length=20, null=True, blank=True)
    date_expired = models.DateField(null=True)
    date_created = models.DateField(null=True)

    def __str__(self):
        suppName = 'Unknown Supply'
        if self.supply_in_storage:
            suppName = self.supply_in_storage.name

        return f'Товар: {suppName} | Для заказа №{self.supply_for.id}: {self.supply_for.place.name}, {self.supply_for.place.city} от {self.date_created.strftime("%d/%m/%y")}'

    class Meta:
        verbose_name = 'Товар в замовленні'
        verbose_name_plural = 'Товари в замовленнях'





