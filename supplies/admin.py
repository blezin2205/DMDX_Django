from django.contrib import admin
from .models import *


admin.site.register(Supply)
admin.site.register(Place)
admin.site.register(Order)
admin.site.register(SupplyInOrder)
admin.site.register(Category)
admin.site.register(ServiceNote)
admin.site.register(Workers)
admin.site.register(GeneralSupply)