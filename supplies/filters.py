import django_filters
from .models import *
from django_filters import CharFilter, ChoiceFilter, ModelChoiceFilter
from django.db.models import Exists, OuterRef, Q, Prefetch
from django.utils import timezone
from django.db.models import Max, Q


class SupplyFilter(django_filters.FilterSet):

    CHOICES = (
        ('dateCreated', 'По даті оновлення'), ('', '')
    )
    name = CharFilter(field_name='name', lookup_expr='icontains', label='Назва товару')
    ref = CharFilter(field_name='ref', lookup_expr='icontains', label='REF')
    ordering = ChoiceFilter(label='Сортування', choices=CHOICES, method='filter_by_order')


    class Meta:
        model = GeneralSupply
        fields = ['name', 'category', 'ref']

    def __init__(self, *args, **kwargs):
        super(SupplyFilter, self).__init__(*args, **kwargs)
        self.filters['ordering'].extra.update(
            {'empty_label': 'A-Z'})
        self.filters['category'].extra.update(
            {'empty_label': 'Всі'})


    def filter_by_order(self, queryset, name, value):

        if value == 'dateCreated':
            return  queryset.annotate(max_date=Max('general__dateCreated')).order_by('-max_date')
        # elif value =='dateGood':
        #     # suppies = GeneralSupply.objects.prefetch_related(
        #     #     Prefetch('general', queryset=Supply.objects.filter(expiredDate__gte=timezone.now().date())))
        #     retSupp = queryset.annotate(date_expred=Q('general__expiredDate')).filter(date_expred__gte=timezone.now().date())
        #     return retSupp.order_by('name')
        # elif value =='dateExpired':
        #     suppies = GeneralSupply.objects.prefetch_related(Prefetch('general', queryset=Supply.objects.filter(expiredDate__lt=timezone.now().date())))
        #     retSupp = suppies.distinct().filter(general__expiredDate__lt=timezone.now().date())
        #     return retSupp.order_by('name')


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

