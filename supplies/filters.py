import django_filters
from .models import *
from django_filters import CharFilter, ChoiceFilter, ModelChoiceFilter
from django.db.models import Exists, OuterRef, Q, Prefetch
from django.utils import timezone


class ChildSupplyFilter(django_filters.FilterSet):
    CHOICES = (
        ('onlyExpired', 'Прострочені'), ('onlyGood', 'Придатні'), ('dateCreated', 'Оновлено')
    )
    name = CharFilter(field_name='general_supply__name', lookup_expr='icontains', label='Назва товару')
    ref = CharFilter(field_name='general_supply__ref', lookup_expr='icontains', label='REF')
    ordering = ChoiceFilter(label='Сортування', choices=CHOICES, method='filter_by_order')

    class Meta:
        model = Supply
        fields = ['category', 'ref', 'supplyLot', 'name', 'ordering']

    def __init__(self, *args, **kwargs):
        super(ChildSupplyFilter, self).__init__(*args, **kwargs)
        self.filters['ordering'].extra.update(
            {'empty_label': 'Всі'})

    def filter_by_category(self, queryset, name, value):
          return queryset.filter(general_supply__category__name__exact=value)

    def filter_by_order(self, queryset, name, value):

        if value == 'onlyGood':
            return  queryset.filter(expiredDate__gte=timezone.now().date()).order_by('expiredDate').distinct()
        elif value =='onlyExpired':
            return queryset.filter(expiredDate__lt=timezone.now().date()).order_by('-expiredDate').distinct()
        elif value =='dateCreated':
            return queryset.order_by('-dateCreated').distinct()


class SupplyFilter(django_filters.FilterSet):

    class EXIST_CHOICES(models.TextChoices):
        В_наявності = "onlyExistChild"
        Немає_в_наявності = "onlyNotExistChild"
        Тільки_придатні = "onlyGood"
        Тільки_прострочені = "onlyExpired"

    CHOICES = (
        ('onlyExistChild', 'В наявності'), ('onlyNotExistChild', 'Немає в наявності')
    )
    name = CharFilter(field_name='name', lookup_expr='icontains', label='Назва товару')
    ref = CharFilter(field_name='ref', lookup_expr='icontains', label='REF')
    ordering = ChoiceFilter(label='Сортування', choices=EXIST_CHOICES.choices, method='filter_by_order')


    class Meta:
        model = GeneralSupply
        fields = ['name', 'category', 'ref', 'ordering']

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
        elif value == 'onlyGood':
            sups = Supply.objects.filter(expiredDate__gte=timezone.now().date())
            prefetch = Prefetch('general', queryset=sups)
            supplies = queryset.prefetch_related(prefetch).filter(general__in=sups).distinct().order_by(
                'name')
            return supplies
        elif value == 'onlyExpired':
            sups = Supply.objects.filter(expiredDate__lt=timezone.now().date())
            prefetch = Prefetch('general', queryset=sups)
            supplies = queryset.prefetch_related(prefetch).filter(general__in=sups).distinct().order_by(
                'name')
            return supplies





class ServiceNotesFilter(django_filters.FilterSet):
    from_user = ModelChoiceFilter(queryset=CustomUser.objects.filter(groups__name='engineer'))
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


class DeviceFilter(django_filters.FilterSet):
    serial_number = CharFilter(field_name='serial_number', lookup_expr='icontains', label='Серійний номер')
    class Meta:
        model = Device
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(DeviceFilter, self).__init__(*args, **kwargs)
        self.filters['in_place'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['general_device'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['in_city'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['in_place'].label = "Клієнт"
        self.filters['general_device'].label = "Прилад"
        self.filters['in_city'].label = "Місто"


class PlaceFilter(django_filters.FilterSet):
    class Meta:
        model = Place
        fields =  '__all__'

    def __init__(self, *args, **kwargs):
        super(PlaceFilter, self).__init__(*args, **kwargs)
        self.filters['city_ref'].label = "Місто"


class CityFilter(django_filters.FilterSet):
    class Meta:
        model = City
        fields =  '__all__'

    def __init__(self, *args, **kwargs):
        super(CityFilter, self).__init__(*args, **kwargs)
        self.filters['name'].label = "Місто"