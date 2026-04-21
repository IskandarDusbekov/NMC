from __future__ import annotations

from decimal import Decimal

from django.db.models import Case, Count, ExpressionWrapper, F, FloatField, Q, Sum, Value, When
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
        completed_work_item_count=Count(
            'work_items',
            filter=Q(work_items__status=WorkItem.Status.COMPLETED),
            distinct=True,
        ),
    ).annotate(
        progress_average=Case(
            When(work_item_count=0, then=Value(0.0)),
            default=ExpressionWrapper(
                Value(100.0) * F('completed_work_item_count') / F('work_item_count'),
                output_field=FloatField(),
            ),
            output_field=FloatField(),
        ),
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
