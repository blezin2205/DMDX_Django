import django_filters
from .models import *
from django_filters import CharFilter, ChoiceFilter, ModelChoiceFilter
from django.db.models import Exists, OuterRef, Q, Prefetch
from django.utils import timezone
from django.db.models import Max, Q


class ChildSupplyFilter(django_filters.FilterSet):
    name = CharFilter(field_name='general_supply__name', lookup_expr='icontains', label='Назва товару')
    ref = CharFilter(field_name='general_supply__ref', lookup_expr='icontains', label='REF')
    class Meta:
        model = Supply
        fields = ['category', 'ref', 'supplyLot', 'id' , 'name']


class SupplyFilter(django_filters.FilterSet):

    CHOICES = (
        ('onlyExistChild', 'В наявності'), ('onlyNotExistChild', 'Немає в наявності')
    )
    name = CharFilter(field_name='name', lookup_expr='icontains', label='Назва товару')
    ref = CharFilter(field_name='ref', lookup_expr='icontains', label='REF')
    ordering = ChoiceFilter(label='Сортування', choices=CHOICES, method='filter_by_order')


    class Meta:
        model = GeneralSupply
        fields = ['name', 'category', 'ref', 'ordering', 'id']

    def __init__(self, *args, **kwargs):
        super(SupplyFilter, self).__init__(*args, **kwargs)
        self.filters['ordering'].extra.update(
            {'empty_label': 'A-Z'})
        self.filters['category'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['category'].label = "Категорія"


    def filter_by_order(self, queryset, name, value):

        if value == 'onlyExistChild':
            return  queryset.filter(general__isnull=False).distinct()
        elif value =='onlyNotExistChild':
            return queryset.filter(general__isnull=True).distinct()


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

