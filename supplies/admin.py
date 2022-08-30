from django.contrib import admin
from .models import *
from .NPModels import *


admin.site.register(Supply)
admin.site.register(Place)
admin.site.register(Order)
admin.site.register(SupplyInOrder)
admin.site.register(Category)
admin.site.register(ServiceNote)
admin.site.register(Workers)
admin.site.register(GeneralSupply)
admin.site.register(OrderInCart)
admin.site.register(SupplyInOrderInCart)
admin.site.register(PreorderInCart)
admin.site.register(SupplyInPreorderInCart)
admin.site.register(GeneralDevice)
admin.site.register(Device)
admin.site.register(City)
admin.site.register(SupplyInPreorder)
admin.site.register(PreOrder)
admin.site.register(NPCity)
# admin.site.register(Delivery_Place)
# admin.site.register(NPDeliveryCreatedDetailInfo)
