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