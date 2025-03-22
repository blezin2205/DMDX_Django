from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Множить значення на аргумент"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return '' 