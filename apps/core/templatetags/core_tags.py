from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def dict_get(mapping, key):
    if not mapping:
        return ''
    return mapping.get(key, '')


@register.filter
def money(value):
    if value in (None, ''):
        return '0.00'
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f'{amount:,.2f}'.replace(',', ' ')


@register.simple_tag
def nav_active(path, prefix):
    return str(path).startswith(str(prefix))


@register.filter
def subtract(value, arg):
    try:
        return Decimal(value) - Decimal(arg)
    except (InvalidOperation, TypeError, ValueError):
        return value
