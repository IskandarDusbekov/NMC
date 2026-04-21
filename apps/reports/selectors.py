from django.db.models import Sum
from django.db.models.functions import Coalesce

from apps.finance.selectors import category_summary, transaction_list
from apps.workforce.models import SalaryPayment


def report_transactions(filters):
    return transaction_list(filters)


def worker_payment_report(filters):
    queryset = SalaryPayment.objects.select_related('worker', 'object')
    if filters.get('date_from'):
        queryset = queryset.filter(date__gte=filters['date_from'])
    if filters.get('date_to'):
        queryset = queryset.filter(date__lte=filters['date_to'])
    if filters.get('currency'):
        queryset = queryset.filter(currency=filters['currency'])
    if filters.get('object'):
        queryset = queryset.filter(object=filters['object'])
    if filters.get('worker'):
        queryset = queryset.filter(worker=filters['worker'])
    return queryset


def category_report(filters):
    return category_summary(filters=filters)


def report_totals(queryset):
    return queryset.values('currency', 'type').annotate(total=Coalesce(Sum('amount'), 0))
