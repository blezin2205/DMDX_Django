import django_filters
from .models import *
from django import forms
from django_filters import CharFilter, ChoiceFilter, ModelChoiceFilter
from django.db.models import Exists, OuterRef, Q, Prefetch, CharField
from django.db.models.functions import Cast
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
        related = queryset.select_related('general_supply', 'general_supply__category')

        if value == 'onlyGood':
            return related.filter(expiredDate__gte=timezone.now().date()).order_by('expiredDate').distinct()
        elif value == 'onlyExpired':
            return related.filter(expiredDate__lt=timezone.now().date()).order_by('-expiredDate').distinct()
        elif value == 'dateCreated':
            return related.order_by('-dateCreated').distinct()


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

    isComplete = ChoiceFilter(choices=ADDRESSED_CHOICES, label='Status', method='filter_by_is_complete')
    PRIVATE_CHOICES = (
        ('1', 'Приватні'),
        ('0', 'Державні')
    )

    NP_DELIVERY_STATE = (
        ('1', 'Одержані'),
        ('0', 'В очікуванні')
    )

    DATE_TO_SEND_CHOICES = (
        ('today', 'Відправка сьогодні'),
        ('expired', 'Просрочена дата відправки'),
    )

    for_state_of_client = ChoiceFilter(choices=PRIVATE_CHOICES, label='Тип організації', method='filter_by_state_of_client')
    for_np_delivery_state = ChoiceFilter(choices=NP_DELIVERY_STATE, label='НП Статус', method='filter_by_state_of_np')
    for_date_to_send = ChoiceFilter(
        choices=DATE_TO_SEND_CHOICES,
        label='Дата відправки',
        method='filter_by_date_to_send',
    )
    search_text = CharFilter(method='filter_by_search_text', label='Пошук...')

    class Meta:
        model = Order
        fields = [
            'isComplete',
            'for_state_of_client',
            'for_np_delivery_state',
            'for_date_to_send',
            'search_text',
        ]

    def __init__(self, *args, **kwargs):
        super(OrderFilter, self).__init__(*args, **kwargs)
        self.filters['isComplete'].label = "Готовність"
        self.filters['isComplete'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['for_state_of_client'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['for_np_delivery_state'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['for_date_to_send'].extra.update(
            {'empty_label': 'Всі'})
        self.filters['search_text'].field.widget.attrs.update({
            'placeholder': 'Місто / Організація / № замовлення'
        })

    def filter_by_is_complete(self, queryset, name, value):
        if value == '1':
            return queryset.filter(isComplete=True)
        if value == '0':
            return queryset.filter(isComplete=False)
        return queryset

    def filter_by_state_of_client(self, queryset, name, value):
        if value == '1':
            return queryset.filter(place__isPrivatePlace=True)
        elif value == '0':
            return queryset.filter(place__isPrivatePlace=False)

    def filter_by_state_of_np(self, queryset, name, value):
        np_for_order = StatusNPParselFromDoucmentID.objects.filter(for_order_id=OuterRef('pk'))
        if value == '1':
            return queryset.filter(Exists(np_for_order.filter(status_code='9')))
        elif value == '0':
            excluded_status_codes = [1, 2, 3, 4, 41, 5, 6, 7, 8, 10, 11, 12, 101, 102, 103, 104, 105, 106, 111, 112]
            return queryset.filter(Exists(np_for_order.filter(status_code__in=excluded_status_codes)))

    def filter_by_date_to_send(self, queryset, name, value):
        if not value:
            return queryset
        today = timezone.localdate()
        qs = queryset.filter(isComplete=False, dateToSend__isnull=False)
        if value == 'today':
            return qs.filter(dateToSend=today)
        if value == 'expired':
            return qs.filter(dateToSend__lt=today)
        return queryset

    def filter_by_search_text(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.annotate(
            order_id_str=Cast('id', output_field=CharField())
        ).filter(
            Q(place__city_ref__name__icontains=value)
            | Q(place__city__icontains=value)
            | Q(place__name__icontains=value)
            | Q(order_id_str__icontains=value)
        ).distinct()


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
        lots_qs = Supply.objects.order_by('expiredDate', 'id')
        gen_prefetch = Prefetch('general', queryset=lots_qs)
        has_lot = Exists(Supply.objects.filter(general_supply_id=OuterRef('pk')))

        if value == 'onlyExistChild':
            return (
                queryset.select_related('category')
                .filter(has_lot)
                .prefetch_related(gen_prefetch)
            )
        elif value == 'onlyNotExistChild':
            return (
                queryset.select_related('category')
                .filter(~has_lot)
                .prefetch_related(gen_prefetch)
            )
        elif value == 'onlyGood':
            today = timezone.now().date()
            good_lots = Supply.objects.filter(
                general_supply_id=OuterRef('pk'),
                expiredDate__gte=today,
            )
            good_lots_qs = Supply.objects.filter(expiredDate__gte=today).order_by('expiredDate', 'id')
            return (
                queryset.select_related('category')
                .filter(Exists(good_lots))
                .prefetch_related(Prefetch('general', queryset=good_lots_qs))
                .order_by('name')
            )
        elif value == 'onlyExpired':
            today = timezone.now().date()
            expired_lots = Supply.objects.filter(
                general_supply_id=OuterRef('pk'),
                expiredDate__lt=today,
            )
            expired_lots_qs = Supply.objects.filter(expiredDate__lt=today).order_by('expiredDate', 'id')
            return (
                queryset.select_related('category')
                .filter(Exists(expired_lots))
                .prefetch_related(Prefetch('general', queryset=expired_lots_qs))
                .order_by('name')
            )
        # A-Z / порожнє ordering — ті самі лоти, що в "В наявності", без додаткового filter
        return (
            queryset.select_related('category')
            .prefetch_related(gen_prefetch)
            .order_by('name')
        )





from .query_utils import places_for_filter_queryset, place_choice_label


def _configure_place_choice_filter(filter_obj):
    place_qs = places_for_filter_queryset()
    filter_obj.queryset = place_qs
    filter_obj.field.queryset = place_qs
    filter_obj.field.label_from_instance = place_choice_label


class ServiceNotesFilter(django_filters.FilterSet):
    from_user = ModelChoiceFilter(queryset=CustomUser.objects.filter(groups__name='engineer'))
    class Meta:
        model = ServiceNote
        fields = ['for_place', 'from_user']

    def __init__(self, *args, **kwargs):
        super(ServiceNotesFilter, self).__init__(*args, **kwargs)
        _configure_place_choice_filter(self.filters['for_place'])
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
        _configure_place_choice_filter(self.filters['in_place'])
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
        # Exists замість JOIN + distinct — інакше на проді з великим обсягом даних запит >30 с (Heroku H12).
        if 'booked_supplies' in value:
            queryset = queryset.filter(
                Exists(SupplyInBookedOrder.objects.filter(supply_for_place_id=OuterRef('pk')))
            )
        if 'preorders' in value:
            queryset = queryset.filter(
                Exists(PreOrder.objects.filter(place_id=OuterRef('pk')))
            )
        if 'orders' in value:
            queryset = queryset.filter(
                Exists(Order.objects.filter(place_id=OuterRef('pk')))
            )
        if 'service_notes' in value:
            queryset = queryset.filter(
                Exists(ServiceNote.objects.filter(for_place_id=OuterRef('pk')))
            )
        if 'devices' in value:
            queryset = queryset.filter(
                Exists(Device.objects.filter(in_place_id=OuterRef('pk')))
            )
        return queryset

    def filter_by_preorder_type(self, queryset, name, value):
        if not value:
            return queryset
            
        if value == 'has_current_month_preorders':
            current_date = timezone.now()
            start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(
                Exists(PreOrder.objects.filter(
                    place_id=OuterRef('pk'),
                    dateCreated__gte=start_of_month,
                ))
            )
            
        elif value == 'needs_order_this_month':
            current_date = timezone.now()
            start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
            end_of_month = (current_date.replace(day=1) + timezone.timedelta(days=32)).replace(day=1).date() - timezone.timedelta(days=1)

            place_ids = list(
                queryset.filter(
                    Exists(PreOrder.objects.filter(place_id=OuterRef('pk')))
                ).values_list('pk', flat=True)
            )
            from .analytics import bulk_predict_next_order_dates
            predictions = bulk_predict_next_order_dates(place_ids)
            places_needing_order = [
                pid for pid, predicted in predictions.items()
                if predicted and start_of_month <= predicted <= end_of_month
            ]
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