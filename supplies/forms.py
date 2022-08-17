import requests

from .models import *
from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from bootstrap_modal_forms.forms import BSModalModelForm


class GeneralSupplyForm(ModelForm):
    class Meta:
        model = GeneralSupply
        fields = '__all__'

class ClientForm(ModelForm):
    class Meta:
        model = Place
        exclude = ['city', 'user']


class WorkerForm(ModelForm):
    class Meta:
        model = Workers
        exclude = ['for_place']


class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password1', 'password2' ]


class LoginForm(AuthenticationForm):
    class Meta:
      model = User
      fields = '__all__'


class ServiceNoteForm(ModelForm):
    class Meta:
      model = ServiceNote
      fields = ['description', 'for_place']

    def __init__(self, *args, **kwargs):
        super(ServiceNoteForm, self).__init__(*args, **kwargs)
        self.fields['description'].label = "Опис виконаних робіт"
        self.fields['for_place'].label = "Клієнт"


class SupplyForm(ModelForm):
    class Meta:
        model = Supply
        fields = ['supplyLot', 'count', 'expiredDate']


class NewSupplyForm(ModelForm):
    class Meta:
        model = Supply
        fields = ['supplyLot', 'count', 'expiredDate', 'name', 'ref', 'category']

class NewGeneralSupplyForm(ModelForm):
    class Meta:
        model = GeneralSupply
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(NewGeneralSupplyForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = "Назва"
        self.fields['ref'].label = "REF"
        self.fields['category'].label = "Категорія"


class OrderInCartForm(ModelForm):
    class Meta:
        model = OrderInCart
        fields = ['place', 'comment', 'isComplete']


class OrderForm(forms.Form):
    order = forms.ModelChoiceField(queryset=Order.objects.filter(isComplete=False))


class PreOrderForm(forms.Form):
    order = forms.ModelChoiceField(queryset=PreOrder.objects.filter(isComplete=False))


class DeviceForm(ModelForm):
    class Meta:
        model = Device
        exclude = ['in_place', 'in_city']

    def __init__(self, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)
        self.fields['general_device'].label = "Прилад"
        self.fields['serial_number'].label = "Серійний номер"
        self.fields['date_installed'].label = "Дата інсталяції"

