from django import template
from ..models import *

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


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.filter(name='in_cart')
def has_group(supId, user):
    try:
       sups =  SupplyInOrderInCart.objects.get(pk=supId)
       return True
    except:
        return False


@register.filter(name='in_precart')
def has_group(supId, user):
    try:
       preorderInCart = PreorderInCart.objects.get(userCreated=user)
       sups =  SupplyInPreorderInCart.objects.get(supply_id=supId, supply_for_order=preorderInCart)
       return True
    except:
        return False

@register.filter(name='in_precart_general')
def has_group(supId, user):
    try:
       preorderInCart = PreorderInCart.objects.get(userCreated=user)
       sups =  SupplyInPreorderInCart.objects.get(general_supply_id=supId, supply_for_order=preorderInCart)
       return True
    except:
        return False