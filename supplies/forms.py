import datetime

import requests
from django.urls import reverse_lazy
from .models import *
from django.forms import ModelForm, Form
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, MultiField, Div
from django.forms import formset_factory


class CreateNPParselForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_action = reverse_lazy('create_np_document_for_order', kwargs={'order_id': self.instance.id})
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Підтвердити'))

        self.fields['payment_user_type'].label = "Хто платить за доставку"
        self.fields['payment_money_type'].label = "Тип оплати"
        self.fields['width'].label = "Ширина (см)"
        self.fields['length'].label = "Довжина (см)"
        self.fields['height'].label = "Висота (см)"
        self.fields['weight'].label = "Фактична вага (кг)"
        self.fields['seatsAmount'].label = "Кількість місць"
        self.fields['description'].label = "Опис"
        self.fields['cost'].label = "Оціночна вартість (грн)"
        self.fields['dateDelivery'].label = "Дата відправки"
        self.fields['sender_np_place'].label = "Відділення відправки"


    payment_user_type = forms.ChoiceField(choices=CreateParselModel.PaymentUserType.choices)
    payment_money_type = forms.ChoiceField(choices=CreateParselModel.PaymentMoneyType.choices)
    dateDelivery = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'min': datetime.datetime.now().date()}), initial=datetime.datetime.now())

    class Meta:
        model = CreateParselModel
        fields = '__all__'



class GeneralSupplyForm(ModelForm):
    class Meta:
        model = GeneralSupply
        fields = '__all__'


class CreateClientForm(ModelForm):
    class Meta:
        model = Place
        exclude = ['city', 'user', 'ref_NP', 'address_NP', 'worker_NP', 'isAddedToNP', 'name_in_NP']

    def __init__(self, *args, **kwargs):
        super(CreateClientForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_action = reverse_lazy('addClient')
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Зберегти'))
        self.fields['name'].label = "Назва організації"
        self.fields['city_ref'].label = "Місто"
        self.fields['address'].label = "Адреса"
        self.fields['link'].label = "Ссилка"
        self.fields['organization_code'].label = "ЄДРПОУ (Якщо поле заповнене, організація буде додана в НП)"


    def clean_organization_code(self):
        orgCode = self.cleaned_data['organization_code']
        print("---didgigs",orgCode.isdigit())
        if orgCode and len(orgCode) != 8:
            raise forms.ValidationError("ЄДРПОУ має 8 цифр!")
        if not orgCode.isdigit():
            raise forms.ValidationError("Тільки цифри")
        return orgCode


class ClientForm(ModelForm):
    class Meta:
        model = Place
        exclude = ['city', 'user', 'ref_NP', 'isAddedToNP', 'name_in_NP']

    def __init__(self, *args, **kwargs):
        super(ClientForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = "Назва організації"
        self.fields['city_ref'].label = "Місто"
        self.fields['address'].label = "Адреса"
        self.fields['link'].label = "Ссилка"
        self.fields['address_NP'].label = "Адреса відправки"
        self.fields['worker_NP'].label = "Контакта особа отримання відправки"
        self.fields['organization_code'].label = "ЄДРПОУ (Якщо поле заповнене, організація буде додана в НП)"
        if self.instance.isAddedToNP:
            self.fields.pop('organization_code')

    def clean_organization_code(self):
        orgCode = self.cleaned_data['organization_code']
        if orgCode and len(orgCode) != 8:
            raise forms.ValidationError("ЄДРПОУ має 8 цифр!")
        if orgCode and not orgCode.isdigit():
            raise forms.ValidationError("Тільки цифри!")
        return orgCode


class ClientFormForParcel(ModelForm):
    class Meta:
        model = Place
        fields = ['address_NP', 'worker_NP']

    def __init__(self, *args, **kwargs):
        super(ClientFormForParcel, self).__init__(*args, **kwargs)
        self.fields['address_NP'].label = "Адреса отримувача"
        self.fields['worker_NP'].label = "Контактна особа-отримувач"


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
        self.fields['position'].label = "Посада"

    def clean_telNumber(self):
        telNumber = self.cleaned_data['telNumber']
        if telNumber and len(str(telNumber)) != 12:
            raise forms.ValidationError("Номер телефону має бути 12 цифр!")
        return telNumber

    def clean_name(self):
        return self.cleaned_data['name'].capitalize()
    def clean_secondName(self):
        return self.cleaned_data['secondName'].capitalize()
    def clean_middleName(self):
        if self.cleaned_data['middleName']:
            return self.cleaned_data['middleName'].capitalize()



class CreateUserForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'password1', 'password2' ]


class LoginForm(AuthenticationForm):
    class Meta:
      model = CustomUser
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
        fields = ['comment', 'isComplete']
    def __init__(self, *args, **kwargs):
        super(OrderInCartForm, self).__init__(*args, **kwargs)
        self.fields['comment'].label = "Комментарій"
        self.fields['isComplete'].label = "Відправлено"


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

