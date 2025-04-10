from django import template
from ..models import *
from django.utils import timezone
from datetime import datetime
import re

register = template.Library()


@register.simple_tag
def my_url(value, field_name, urlencode=None):
    url = '?{}={}'.format(field_name, value)

    if urlencode:
        querystring = urlencode.split('&')
        filtered_querystring = filter(lambda p: p.split('=')[0]!=field_name, querystring)
        encoded_quertstring = '&'.join(filtered_querystring)
        url = '{}&{}'.format(url, encoded_quertstring)

    return url


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
        # Add more extensions and corresponding icons as needed
    }

    default_icon = 'images/default-icon.png'  # Default icon for unknown file types

    # Return the icon URL corresponding to the file extension, or default icon if not found
    return icon_map.get(extension, default_icon)


@register.filter(name='total_counts')
def has_group(sups_in_delivery_order_set):
    total_count = sum(obj.count for obj in sups_in_delivery_order_set)
    return total_count or 0



@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


@register.filter(name='in_cart')
def has_group(supId):
    try:
       sups =  SupplyInOrderInCart.objects.get(pk=supId)
       print(sups.count_in_order)
       return sups.count_in_order
    except:
        return 0


@register.filter(name='in_precart')
def has_group(supId, user):
    try:
       preorderInCart = PreorderInCart.objects.get(userCreated=user)
       sups =  SupplyInPreorderInCart.objects.get(supply_id=supId, supply_for_order=preorderInCart)
       return True
    except:
        return False

@register.filter
def in_precart_general(supId, user):
    try:
       preorderInCart = PreorderInCart.objects.get(userCreated=user)
       sups =  SupplyInPreorderInCart.objects.get(general_supply_id=supId, supply_for_order=preorderInCart)
       return sups.count_in_order
    except:
        return None
    
@register.simple_tag
def in_precart_general_with_place(supId, user, place_id=None):
    try:
       print('place_id', place_id)
       print('user', user)
       preorderInCart = PreorderInCart.objects.get(userCreated=user, place_id=place_id)
       sups =  SupplyInPreorderInCart.objects.get(general_supply_id=supId, supply_for_order=preorderInCart)
       print("count in precart", sups.count_in_order)
       return sups.count_in_order
    except:
        return None    



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