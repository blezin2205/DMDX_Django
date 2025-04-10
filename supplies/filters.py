import django_filters
from .models import *
from django import forms
from django_filters import CharFilter, ChoiceFilter, ModelChoiceFilter
from django.db.models import Exists, OuterRef, Q, Prefetch
from django.utils import timezone
from django.forms.widgets import *


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
        self.filters['category'].label = 'Категорія'
        self.filters['ref'].label = 'REF'
        self.filters['supplyLot'].label = 'LOT'
        self.filters['name'].label = 'Назва'

    def filter_by_category(self, queryset, name, value):
          return queryset.filter(general_supply__category__name__exact=value)

    def filter_by_order(self, queryset, name, value):

        if value == 'onlyGood':
            return queryset.filter(expiredDate__gte=timezone.now().date()).order_by('expiredDate').distinct()
        elif value =='onlyExpired':
            return queryset.filter(expiredDate__lt=timezone.now().date()).order_by('-expiredDate').distinct()
        elif value =='dateCreated':
            return queryset.order_by('-dateCreated').distinct()


class BookedSuppliesFilter(django_filters.FilterSet):
    name = CharFilter(field_name='generalSupply__name', lookup_expr='icontains', label='Назва товару')
    smn = CharFilter(field_name='generalSupply__SMN_code', lookup_expr='icontains', label='SMN')
    ref = CharFilter(field_name='generalSupply__ref', lookup_expr='icontains', label='REF')
    category = django_filters.ModelChoiceFilter(
        field_name='generalSupply__category',
        to_field_name='id',
        queryset=Category.objects.all(),
        label='Category'
    )

    class Meta:
        model = SupplyInBookedOrder
        fields = ['category', 'ref', 'smn', 'name']

    def filter_by_category(self, queryset, name, value):
          return queryset.filter(general_supply__category__name__exact=value)



class OrderFilter(django_filters.FilterSet):
    ADDRESSED_CHOICES = (
        ('1', 'Відправлені'),
        ('0', 'В очікуванні')
    )

    isComplete = ChoiceFilter(choices=ADDRESSED_CHOICES, label='Status')
    PRIVATE_CHOICES = (
        ('1', 'Приватні'),
        ('0', 'Державні')
    )

    NP_DELIVERY_STATE = (
        ('1', 'Одержані'),
        ('0', 'В очікуванні')
    )

    for_state_of_client = ChoiceFilter(choices=PRIVATE_CHOICES, label='Тип організації', method='filter_by_state_of_client')
    for_np_delivery_state = ChoiceFilter(choices=NP_DELIVERY_STATE, label='НП Статус', method='filter_by_state_of_np')

    class Meta:
        model = Order
        fields = ['isComplete', 'for_state_of_client', 'for_np_delivery_state']

    def __init__(self, *args, **kwargs):
        super(OrderFilter, self).__init__(*args, **kwargs)
        self.filters['isComplete'].label = "Готовність"
        self.filters['isComplete'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['for_state_of_client'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['for_np_delivery_state'].extra.update(
            {'empty_label': 'Всі'})

    def filter_by_state_of_client(self, queryset, name, value):
        if value == '1':
            return queryset.filter(place__isPrivatePlace=True)
        elif value == '0':
            return queryset.filter(place__isPrivatePlace=False)

    def filter_by_state_of_np(self, queryset, name, value):
        if value == '1':
            return queryset.filter(statusnpparselfromdoucmentid__status_code=9)
        elif value == '0':
            excluded_status_codes = [1, 2, 3, 4, 41, 5, 6, 7, 8, 10, 11, 12, 101, 102, 103, 104, 105, 106, 111, 112]
            return queryset.filter(statusnpparselfromdoucmentid__status_code__in=excluded_status_codes)


class PreorderFilter(django_filters.FilterSet):
    ADDRESSED_CHOICES = (
        ('1', 'Підтверджені'),
        ('0', 'В очікуванні')
    )

    PREORDER_TYPE_CHOICES = (
        ('1', 'Передзамовлення'),
        ('0', 'Договори')
    )

    PRIVATE_CHOICES = (
        ('1', 'Приватні'),
        ('0', 'Державні')
    )

    isComplete = ChoiceFilter(choices=ADDRESSED_CHOICES, label='Status')
    isPreorder = ChoiceFilter(choices=PREORDER_TYPE_CHOICES, label='Status')
    for_state_of_client = ChoiceFilter(choices=PRIVATE_CHOICES, label='Тип організації',
                                       method='filter_by_state_of_client')
    state_of_delivery = django_filters.MultipleChoiceFilter(choices=PreOrder.STATE_CHOICES, widget=forms.CheckboxSelectMultiple())
    search_text = CharFilter(method='my_custom_filter_search_text', label='Пошук...')
    date_range = django_filters.DateFromToRangeFilter(
        field_name='dateCreated', 
        label='Період створення',
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )

    def my_custom_filter_search_text(self, queryset, name, value):
        return queryset.filter(Q(comment__icontains=value) | Q(place__name__icontains=value) | Q(place__city_ref__name__icontains=value) | Q(place__city__icontains=value))

    STATE_CHOICES = (
        ('Awaiting', 'Очікується'),
        ('Partial', 'Частково поставлено'),
        ('Complete', 'Повністю поставлено'),
    )

    class Meta:
        model = PreOrder
        fields = ['state_of_delivery', 'isComplete', 'for_state_of_client', 'isPreorder', 'search_text', 'date_range']

    def filter_by_state_of_delivery(self, queryset, name, value):
        return queryset.filter(state_of_delivery=value)

    def filter_by_state_of_client(self, queryset, name, value):
        if value == '1':
            return queryset.filter(place__isPrivatePlace=True)
        elif value == '0':
            return queryset.filter(place__isPrivatePlace=False)

    def __init__(self, *args, **kwargs):
        super(PreorderFilter, self).__init__(*args, **kwargs)
        self.filters['isComplete'].label = "Статус"
        self.filters['isComplete'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['isPreorder'].label = "Тип передзамовлення"
        self.filters['isPreorder'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['state_of_delivery'].label = "Статус поставки"
        self.filters['for_state_of_client'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['date_range'].label = "Період створення"


class SupplyFilter(django_filters.FilterSet):

    class EXIST_CHOICES(models.TextChoices):
        В_наявності = "onlyExistChild"
        Немає_в_наявності = "onlyNotExistChild"
        Тільки_придатні = "onlyGood"
        Тільки_прострочені = "onlyExpired"

    CHOICES = (
        ('onlyExistChild', 'В наявності'), ('onlyNotExistChild', 'Немає в наявності')
    )
    name = CharFilter(field_name='name', lookup_expr='icontains', label='Назва', widget=TextInput(attrs={'style': 'min-width: 100px;'}))
    ref = CharFilter(field_name='ref', lookup_expr='icontains', label='REF', widget=TextInput(attrs={'style': 'min-width: 70px;'}))
    SMN_code = CharFilter(field_name='SMN_code', lookup_expr='icontains', label='SMN', widget=TextInput(attrs={'style': 'min-width: 70px;'}))
    ordering = ChoiceFilter(label='Сортування', choices=EXIST_CHOICES.choices, method='filter_by_order')


    class Meta:
        model = GeneralSupply
        fields = ['name', 'category', 'ref', 'SMN_code', 'ordering']

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
        exclude = ['image']

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


import django_filters

class PlaceFilter(django_filters.FilterSet):
    PRIVATE_CHOICES = (
        ('1', 'Приватні'),
        ('0', 'Державні')
    )

    OPTIONS_BUTTON = (
        ('booked_supplies', 'Заброньовані товари'),
        ('preorders', 'Передзамовлення'),
        ('orders', 'Замовлення'),
        ('service_notes', 'Сервісні замітки'),
        ('devices', 'Прилади'),
    )

    PREORDER_FILTER_CHOICES = (
        ('', 'Всі'),
        ('has_current_month_preorders', 'Має передзамовлення за поточний місяць'),
        ('needs_order_this_month', 'Потребує замовлення в цьому місяці'),
    )

    isPrivatePlace = django_filters.ChoiceFilter(choices=PRIVATE_CHOICES, label='Тип організації')
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains', label='Назва')
    city = django_filters.CharFilter(field_name='city', lookup_expr='icontains', label='Місто')
    is_has_options_button = django_filters.MultipleChoiceFilter(choices=OPTIONS_BUTTON,
                                                            widget=forms.CheckboxSelectMultiple(),
                                                            method='filter_by_is_has_options_button')
    preorder_filter = django_filters.ChoiceFilter(choices=PREORDER_FILTER_CHOICES,
                                                label='Фільтр передзамовлень',
                                                method='filter_by_preorder_type')

    class Meta:
        model = Place
        fields = ['isPrivatePlace', 'name', 'city_ref', 'is_has_options_button', 'preorder_filter']

    def __init__(self, *args, **kwargs):
        super(PlaceFilter, self).__init__(*args, **kwargs)
        self.filters['city_ref'].label = "Місто"
        self.filters['is_has_options_button'].label = "Наявність записів"
        self.filters['preorder_filter'].label = "Фільтр передзамовлень"

    def filter_by_is_has_options_button(self, queryset, name, value):
        if 'booked_supplies' in value:
            queryset = queryset.filter(supplyinbookedorder__isnull=False).distinct()
        if 'preorders' in value:
            queryset = queryset.filter(preorder__isnull=False).distinct()
        if 'orders' in value:
            queryset = queryset.filter(order__isnull=False).distinct()
        if 'service_notes' in value:
            queryset = queryset.filter(servicenote__isnull=False).distinct()
        if 'devices' in value:
            queryset = queryset.filter(device__isnull=False).distinct()
        return queryset

    def filter_by_preorder_type(self, queryset, name, value):
        if not value:
            return queryset
            
        if value == 'has_current_month_preorders':
            current_date = timezone.now()
            start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(preorder__dateCreated__gte=start_of_month).distinct()
            
        elif value == 'needs_order_this_month':
            current_date = timezone.now()
            start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
            end_of_month = (current_date.replace(day=1) + timezone.timedelta(days=32)).replace(day=1).date() - timezone.timedelta(days=1)
            
            # First filter places that have at least one preorder
            places_with_preorders = queryset.filter(preorder__isnull=False).distinct()
            
            # Then filter based on predicted next order date
            from .analytics import PreorderAnalytics
            places_needing_order = []
            
            for place in places_with_preorders:
                analytics = PreorderAnalytics(place)
                next_order_date = analytics.predict_next_order_date()
                if next_order_date and start_of_month <= next_order_date <= end_of_month:
                    places_needing_order.append(place.id)
            
            return queryset.filter(id__in=places_needing_order)
            
        return queryset



class CityFilter(django_filters.FilterSet):
    name = CharFilter(field_name='name', lookup_expr='icontains', label='Назва міста')

    class Meta:
        model = City
        fields =  '__all__'

    def __init__(self, *args, **kwargs):
        super(CityFilter, self).__init__(*args, **kwargs)
        self.filters['name'].label = "Місто"