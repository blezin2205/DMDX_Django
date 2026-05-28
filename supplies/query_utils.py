"""Безпечні ORM-патерни: COUNT через підзапит замість JOIN + GROUP BY."""
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce

from .models import Place


def related_count_subquery(model, fk_field):
    """
    Корельований COUNT для one-to-many / FK.
    Кілька таких анотацій у одному queryset не дають cartesian product.
    """
    return Coalesce(
        Subquery(
            model.objects.filter(**{fk_field: OuterRef('pk')})
            .values(fk_field)
            .annotate(_cnt=Count('pk'))
            .values('_cnt')[:1],
            output_field=IntegerField(),
        ),
        0,
        output_field=IntegerField(),
    )


def devices_list_queryset(qs):
    """Список приладів: general_device, клієнт і місто в одному запиті."""
    return qs.select_related(
        'general_device',
        'in_place',
        'in_place__city_ref',
        'in_city',
    )


def places_for_filter_queryset():
    """Queryset для ModelChoiceFilter «Клієнт» — Place.__str__ читає city_ref."""
    return Place.objects.select_related('city_ref').order_by('name')


def place_choice_label(place):
    city = (place.city_ref.name if place.city_ref_id and place.city_ref else None) or place.city or '—'
    return f'{place.name}, {city}'


def servicenotes_list_queryset(qs):
    """Сервісні записи: інженер і клієнт з містом без N+1 у таблиці."""
    return qs.select_related(
        'from_user',
        'for_place',
        'for_place__city_ref',
    )
