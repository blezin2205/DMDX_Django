from django import template
from ..models import *
from django.utils import timezone
from datetime import datetime
import re
from ..user_request_cache import (
    ensure_user_group_names,
    order_in_cart_supply_counts,
    precart_row_maps,
)

register = template.Library()


def _coerce_pk(value):
    """Template tags may receive a model instance or a raw primary key."""
    if value is None:
        return None
    pk = getattr(value, 'pk', value)
    return int(pk)


@register.simple_tag
def my_url(value, field_name, urlencode=None):
    url = '?{}={}'.format(field_name, value)

    if urlencode:
        querystring = urlencode.split('&')
        filtered_querystring = filter(lambda p: p.split('=')[0]!=field_name, querystring)
        encoded_quertstring = '&'.join(filtered_querystring)
        url = '{}&{}'.format(url, encoded_quertstring)

    return url


@register.simple_tag
def pagination_page_numbers(page_obj, max_visible=3):
    """
    Список номерів сторінок для компактної пагінації: не більше `max_visible`
    послідовних сторінок навколо поточної (краї обрізаються діапазоном 1..num_pages).
    """
    paginator = page_obj.paginator
    num_pages = paginator.num_pages
    current = page_obj.number
    try:
        max_visible = int(max_visible)
    except (TypeError, ValueError):
        max_visible = 3
    if max_visible < 1:
        max_visible = 1
    if num_pages <= max_visible:
        return list(range(1, num_pages + 1))
    half = max_visible // 2
    start = current - half
    end = start + max_visible - 1
    if start < 1:
        start = 1
        end = max_visible
    if end > num_pages:
        end = num_pages
        start = num_pages - max_visible + 1
    return list(range(start, end + 1))


@register.filter(name='total_values_count')
def total_values_count(dictionary):
    if isinstance(dictionary, dict):
        return sum(len(value) if isinstance(value, (list, tuple)) else 1 for value in dictionary.values())
    return 0

@register.filter(name='endswith')
def endswith(value, arg):
    return value.endswith(arg)


@register.filter
def get_file_icon_url(filename):
    extension = filename.split('.')[-1].lower()  # Get file extension (convert to lowercase)

    # Define a mapping of file extensions to their corresponding icon URLs
    icon_map = {
        'pdf': 'images/pdf-icon.png',
        'doc': 'images/doc-icon.png',
        'docx': 'images/docx-icon.png',
        'xls': 'images/xls-icon.png',
        'zip': 'images/zip-icon.png',
        'rar': 'images/rar-icon.png',
        'xlsx': 'images/xls-icon.png',
        'ppt': 'images/ppt-icon.png',
        'pptx': 'images/ppt-icon.png',
        'jpg': 'images/img-icon.png',
        'jpeg': 'images/img-icon.png',
        'png': 'images/img-icon.png',
        # Add more extensions to the mapping as needed
    }

    default_icon = 'images/default-icon.png'  # Default icon for unknown file extensions

    # Return the icon URL corresponding to the file extension, or default icon if not found
    return icon_map.get(extension, default_icon)


@register.filter(name='total_counts')
def has_group(sups_in_delivery_order_set):
    total_count = sum(obj.count for obj in sups_in_delivery_order_set)
    return total_count or 0



@register.filter(name='has_group')
def has_group(user, group_name):
    if not getattr(user, 'is_authenticated', False):
        return False
    return group_name in ensure_user_group_names(user)



@register.simple_tag(takes_context=True)
def supply_in_cart_count(context, supp):
    """One cart lookup per request; avoids N+1 from add_cart_button per LOT row."""
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return 0
    mapping = order_in_cart_supply_counts(request.user)
    return int(mapping.get(supp.id, 0) or 0)


@register.filter(name='in_cart')
def in_cart_placeholder(sup_id):
    """Deprecated: use {% supply_in_cart_count supp %} (needs request in context)."""
    return 0


@register.filter(name='in_precart')
def in_precart(supId, user):
    if not getattr(user, 'is_authenticated', False):
        return False
    supply_ids, _general = precart_row_maps(user)
    pk = _coerce_pk(supId)
    if pk is None:
        return False
    return pk in supply_ids



@register.filter
def in_precart_general(supId, user):
    if not getattr(user, 'is_authenticated', False):
        return None
    _supply_ids, general_counts = precart_row_maps(user)
    pk = _coerce_pk(supId)
    if pk is None:
        return None
    val = general_counts.get(pk)
    return val if val is not None else None


@register.simple_tag(takes_context=True)
def in_precart_general_with_place(context, supId, user, place_id=None):
    if not getattr(user, 'is_authenticated', False):
        return 0
    _supply_ids, general_counts = precart_row_maps(user, place_id=place_id)
    pk = _coerce_pk(supId)
    if pk is None:
        return 0
    return int(general_counts.get(pk, 0) or 0)


@register.filter
def next(some_list, current_index):
    """
    Returns the next element of the list using the current index if it exists.
    Otherwise returns an empty string.
    """
    try:
        return some_list[int(current_index) + 1] # access the next element
    except:
        return '' # return empty string in case of exception

@register.filter
def previous(some_list, current_index):
    """
    Returns the previous element of the list using the current index if it exists.
    Otherwise returns an empty string.
    """
    try:
        return some_list[int(current_index) - 1] # access the previous element
    except:
        return '' # return empty string in case of exception

@register.filter
def date_color(date):
    if not date:
        return 'red'

    today = timezone.now().date()

    # Handle both datetime and date objects
    if hasattr(date, 'date'):
        date = date.date()

    if date > today:
        return 'blue'
    elif date == today:
        return 'orange'
    else:
        return 'red'

@register.filter
def is_mobile(request):
    """
    Detects if the request is from a mobile device.
    Returns True if the request is from a mobile device, False otherwise.
    """
    if not request:
        return False

    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    mobile_keywords = ['android', 'iphone', 'ipad', 'ipod', 'windows phone', 'mobile']

    return any(keyword in user_agent for keyword in mobile_keywords)


@register.filter
def last_seen_ago(value):
    if not value:
        return 'ніколи'
    seconds = int((timezone.now() - value).total_seconds())
    if seconds < 60:
        return 'щойно'
    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes} хв тому'
    hours = minutes // 60
    if hours < 24:
        return f'{hours} год тому'
    days = hours // 24
    return f'{days} дн тому'
