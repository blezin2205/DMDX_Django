from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth.signals import user_logged_in
from enum import Enum


class CargoType(Enum):
    PARCEL = "Parcel"
    CARGO = "Cargo"
    DOCUMENTS = "Documents"
    TIRES_WHEELS = "TiresWheels"
    PALLET = "Pallet"

    @classmethod
    def choices(cls):
        return [(member.value, cls.get_description(member.value)) for member in cls]

    @classmethod
    def get_description(cls, value):
        descriptions = {
            "Parcel": "Посилка",
            "Cargo": "Вантаж",
            "Documents": "Документи",
            "TiresWheels": "Шини-диски",
            "Pallet": "Палети"
        }
        return descriptions.get(value, "")

class NPCity(models.Model):
    name = models.CharField(max_length=100, null=True)
    ref = models.CharField(max_length=100, null=True)
    area = models.CharField(max_length=100, null=True)
    settlementType = models.CharField(max_length=100, null=True)
    cityID = models.CharField(max_length=100, null=True)
    settlementTypeDescription = models.CharField(max_length=100, null=True)
    areaDescription = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Нова Пошта - Місто'
        verbose_name_plural = 'Нова Пошта - Міста'