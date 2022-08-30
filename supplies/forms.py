import datetime

import requests
from django.urls import reverse_lazy
from .models import *
from django.forms import ModelForm, Form
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from  crispy_forms.layout import Submit



class CreateNPParselForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_action = reverse_lazy('create_np_document_for_order', kwargs={'order_id': self.instance.id})
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Підтвердити'))

        self.fields['payment_user_type'].label = "Хто платить за доставку"
        self.fields['payment_money_type'].label = "Тип оплати"
        self.fields['width'].label = "Ширина"
        self.fields['length'].label = "Довжина"
        self.fields['height'].label = "Висота"
        self.fields['weight'].label = "Фактична вага"
        self.fields['seatsAmount'].label = "Кількість місць"
        self.fields['description'].label = "Опис"
        self.fields['cost'].label = "Оціночна вартість"
        self.fields['dateDelivery'].label = "Дата відправки"


    payment_user_type = forms.ChoiceField(choices=CreateParselModel.PaymentUserType.choices)
    payment_money_type = forms.ChoiceField(choices=CreateParselModel.PaymentMoneyType.choices)
    dateDelivery = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'min': datetime.datetime.now().date()}))

    # def clean_width(self):
    #     width = self.cleaned_data['width']
    #     print(f'CLEAN WIDTH {width}')
    #     print(width < 10)
    #     if width < 10:
    #         print()
    #         raise forms.ValidationError("Поле обов'язкове!")
    #     return width


    class Meta:
        model = CreateParselModel
        fields = '__all__'



class GeneralSupplyForm(ModelForm):
    class Meta:
        model = GeneralSupply
        fields = '__all__'

class ClientForm(ModelForm):
    class Meta:
        model = Place
        exclude = ['city', 'user', 'ref_NP']

    def __init__(self, *args, **kwargs):
        super(ClientForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = "Назва організації"
        self.fields['city_ref'].label = "Місто"
        self.fields['address'].label = "Адреса"
        self.fields['link'].label = "Ссилка"
        self.fields['organization_code'].label = "ЄДРПОУ (Якщо поле заповнене, організація буде додана в НП)"
        self.fields['address_NP'].label = "Адреса відправки"
        self.fields['worker_NP'].label = "Контакта особа отримання відправки"


class WorkerForm(ModelForm):
    class Meta:
        model = Workers
        exclude = ['for_place', 'ref_NP', 'ref_counterparty_NP']

    def __init__(self, *args, **kwargs):
        super(WorkerForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = "Ім'я"
        self.fields['secondName'].label = "Прізвище"
        self.fields['middleName'].label = "По-батькові"
        self.fields['telNumber'].label = "Телефон в форматі 38..."
        self.fields['position'].label = "посада"


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

