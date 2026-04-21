from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count, FloatField, Q, Sum, Value
from django.db.models.functions import Coalesce

from apps.finance.models import CurrencyChoices, TransactionTypeChoices

from .models import ConstructionObject, WorkItem


ZERO = Decimal('0.00')


def construction_object_queryset():
    return ConstructionObject.objects.annotate(
        total_expense_uzs=Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(
                    transactions__type=TransactionTypeChoices.EXPENSE,
                    transactions__currency=CurrencyChoices.UZS,
                    transactions__is_deleted=False,
                ),
            ),
            ZERO,
        ),
        total_expense_usd=Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(
                    transactions__type=TransactionTypeChoices.EXPENSE,
                    transactions__currency=CurrencyChoices.USD,
                    transactions__is_deleted=False,
                ),
            ),
            ZERO,
        ),
        work_item_count=Count('work_items', distinct=True),
        progress_average=Coalesce(Avg('work_items__progress_percent'), Value(0.0), output_field=FloatField()),
    )


def work_item_queryset():
    return WorkItem.objects.select_related('object', 'assigned_worker').annotate(
        paid_amount=Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(
                    transactions__type=TransactionTypeChoices.EXPENSE,
                    transactions__is_deleted=False,
                ),
            ),
            ZERO,
        ),
        paid_amount_uzs=Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(
                    transactions__type=TransactionTypeChoices.EXPENSE,
                    transactions__currency=CurrencyChoices.UZS,
                    transactions__is_deleted=False,
                ),
            ),
            ZERO,
        ),
        paid_amount_usd=Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(
                    transactions__type=TransactionTypeChoices.EXPENSE,
                    transactions__currency=CurrencyChoices.USD,
                    transactions__is_deleted=False,
                ),
            ),
            ZERO,
        ),
    )
