from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import CurrencyChoices, ManagerAccount, ManagerTransfer, Transaction, TransactionTypeChoices, WalletTypeChoices


ZERO = Decimal('0.00')
CHART_COLORS = ['#2563eb', '#f59e0b', '#8b5cf6', '#ef4444', '#14b8a6', '#64748b', '#22c55e', '#f97316']


def _percent(value, total):
    if not total:
        return 0
    return int((Decimal(value) / Decimal(total)) * Decimal('100'))


def _today():
    return timezone.now().date()


def transaction_list(filters=None, user=None):
    queryset = Transaction.objects.active().select_related(
        'category',
        'object',
        'work_item',
        'worker',
        'created_by',
        'manager_account__user',
    )
    filters = filters or {}
    if user and getattr(user, 'is_authenticated', False) and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
        manager_account = getattr(user, 'manager_account', None)
        queryset = queryset.filter(manager_account=manager_account, wallet_type=WalletTypeChoices.MANAGER)
    if filters.get('date_from'):
        queryset = queryset.filter(date__gte=filters['date_from'])
    if filters.get('date_to'):
        queryset = queryset.filter(date__lte=filters['date_to'])
    if filters.get('currency'):
        queryset = queryset.filter(currency=filters['currency'])
    if filters.get('object'):
        queryset = queryset.filter(object=filters['object'])
    if filters.get('work_item'):
        queryset = queryset.filter(work_item=filters['work_item'])
    if filters.get('worker'):
        queryset = queryset.filter(worker=filters['worker'])
    if filters.get('category'):
        queryset = queryset.filter(category=filters['category'])
    if filters.get('transaction_type'):
        queryset = queryset.filter(type=filters['transaction_type'])
    if filters.get('wallet_type'):
        queryset = queryset.filter(wallet_type=filters['wallet_type'])
    if filters.get('manager_account'):
        queryset = queryset.filter(manager_account=filters['manager_account'])
    if filters.get('search'):
        queryset = queryset.filter(description__icontains=filters['search'])
    return queryset


def recent_transactions(limit=8, user=None):
    return transaction_list(user=user)[:limit]


def recent_transfers(limit=8, user=None):
    queryset = ManagerTransfer.objects.select_related('to_manager__user', 'from_user')
    if user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
        queryset = queryset.filter(to_manager=getattr(user, 'manager_account', None))
    return queryset[:limit]


def manager_accounts(user=None):
    queryset = ManagerAccount.objects.select_related('user').filter(is_active=True)
    if user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
        queryset = queryset.filter(user=user)
    return queryset


def top_manager_spending(limit=5):
    rows = (
        Transaction.objects.manager_wallet()
        .filter(type=TransactionTypeChoices.EXPENSE)
        .values('manager_account__user__full_name', 'currency')
        .annotate(total=Coalesce(Sum('amount'), ZERO))
        .order_by('-total')[:limit]
    )
    return rows


def category_summary(transaction_type=TransactionTypeChoices.EXPENSE, filters=None, user=None):
    queryset = transaction_list(filters, user=user).filter(type=transaction_type, category__isnull=False)
    rows = (
        queryset.values('category__name', 'currency')
        .annotate(total=Coalesce(Sum('amount'), ZERO))
        .order_by('-total')[:8]
    )
    currency_totals = defaultdict(lambda: ZERO)
    for row in rows:
        currency_totals[row['currency']] += row['total']
    return [
        {
            'label': f"{row['category__name']} ({row['currency']})",
            'total': row['total'],
            'currency': row['currency'],
            'percent': _percent(row['total'], currency_totals[row['currency']]),
            'color': CHART_COLORS[index % len(CHART_COLORS)],
        }
        for index, row in enumerate(rows)
    ]


def daily_expense_series(days=7, user=None):
    start = _today() - timedelta(days=days - 1)
    transactions = (
        transaction_list({'date_from': start, 'transaction_type': TransactionTypeChoices.EXPENSE}, user=user)
        .values_list('date', 'currency', 'amount')
    )
    mapping = defaultdict(lambda: {CurrencyChoices.UZS: ZERO, CurrencyChoices.USD: ZERO})
    for transaction_date, currency, amount in transactions:
        mapping[transaction_date][currency] += amount
    rows = [
        {
            'label': (start + timedelta(days=offset)).strftime('%d %b'),
            'UZS': mapping[start + timedelta(days=offset)][CurrencyChoices.UZS],
            'USD': mapping[start + timedelta(days=offset)][CurrencyChoices.USD],
        }
        for offset in range(days)
    ]
    max_uzs = max([row['UZS'] for row in rows] or [ZERO])
    max_usd = max([row['USD'] for row in rows] or [ZERO])
    for row in rows:
        row['UZS_percent'] = _percent(row['UZS'], max_uzs)
        row['USD_percent'] = _percent(row['USD'], max_usd)
    return rows


def monthly_expense_series(months=6, user=None):
    today = _today()
    start_month = today.replace(day=1)
    first_month = start_month
    for _ in range(months - 1):
        first_month = (first_month.replace(day=1) - timedelta(days=1)).replace(day=1)

    transactions = (
        transaction_list({'date_from': first_month, 'transaction_type': TransactionTypeChoices.EXPENSE}, user=user)
        .values_list('date', 'currency', 'amount')
    )
    grouped = defaultdict(lambda: {CurrencyChoices.UZS: ZERO, CurrencyChoices.USD: ZERO})
    for transaction_date, currency, amount in transactions:
        period = transaction_date.replace(day=1)
        grouped[period][currency] += amount

    labels = []
    cursor = first_month
    for _ in range(months):
        labels.append(cursor)
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    rows = [
        {
            'label': period.strftime('%b %Y'),
            'UZS': grouped[period][CurrencyChoices.UZS],
            'USD': grouped[period][CurrencyChoices.USD],
        }
        for period in labels
    ]
    max_uzs = max([row['UZS'] for row in rows] or [ZERO])
    max_usd = max([row['USD'] for row in rows] or [ZERO])
    for row in rows:
        row['UZS_percent'] = _percent(row['UZS'], max_uzs)
        row['USD_percent'] = _percent(row['USD'], max_usd)
    return rows
