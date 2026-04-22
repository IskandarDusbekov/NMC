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


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    request = context.get('request')
    if not request:
        return f'?page={page_number}'
    query = request.GET.copy()
    query['page'] = page_number
    return f'?{query.urlencode()}'


@register.simple_tag
def pagination_window(page_obj, side_count=2):
    current = page_obj.number
    total = page_obj.paginator.num_pages
    pages = {1, total}

    for page in range(current - side_count, current + side_count + 1):
        if 1 <= page <= total:
            pages.add(page)

    ordered_pages = sorted(pages)
    result = []
    previous = None
    for page in ordered_pages:
        if previous is not None and page - previous > 1:
            result.append('...')
        result.append(page)
        previous = page
    return result
