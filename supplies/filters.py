import django_filters
from .models import *
from django_filters import CharFilter, ChoiceFilter, ModelChoiceFilter
from django.forms.widgets import Input, TextInput


class SupplyFilter(django_filters.FilterSet):

    CHOICES = (
        ('dateCreated', 'По даті оновлення'),
        ('dateGood', 'Тільки придатні'),
        ('dateExpired', 'Тільки прострочені'),
    )
    name = CharFilter(field_name='name', lookup_expr='icontains', label='Назва товару')
    ref = CharFilter(field_name='ref', lookup_expr='icontains', label='REF')
    ordering = ChoiceFilter(label='Сортування', choices=CHOICES, method='filter_by_order')
    supplyLot = CharFilter(field_name='supplyLot', lookup_expr='icontains', label='LOT')

    class Meta:
        model = Supply
        fields = ['name', 'category', 'ordering', 'ref', 'supplyLot']

    def __init__(self, *args, **kwargs):
        super(SupplyFilter, self).__init__(*args, **kwargs)
        self.filters['ordering'].extra.update(
            {'empty_label': 'A-Z'})
        self.filters['category'].extra.update(
            {'empty_label': 'Всі'})

        self.filters['category'].label = "Категорія"

    def filter_by_order(self, queryset, name, value):
        expression = ''
        if value == 'dateCreated':
            expression = '-dateCreated'
            return  queryset.order_by(expression)
        elif value =='dateGood':
            return queryset.filter(expiredDate__gte=timezone.now().date()).order_by('expiredDate')
        elif value =='dateExpired':
            return queryset.filter(expiredDate__lte=timezone.now().date()).order_by('-expiredDate')


class ServiceNotesFilter(django_filters.FilterSet):
    class Meta:
        model = ServiceNote
        fields = ['for_place', 'from_user']

    def __init__(self, *args, **kwargs):
        super(ServiceNotesFilter, self).__init__(*args, **kwargs)
        self.filters['from_user'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['for_place'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['from_user'].label = "Інженер"
        self.filters['for_place'].label = "Клієнт"

