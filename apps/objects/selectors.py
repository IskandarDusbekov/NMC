from __future__ import annotations

from decimal import Decimal

from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, FloatField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce

from apps.finance.models import CurrencyChoices, TransactionTypeChoices
from apps.finance.models import Transaction

from .models import ConstructionObject, WorkItem


ZERO = Decimal('0.00')


def construction_object_queryset():
    expense_totals = (
        Transaction.objects.active()
        .filter(object_id=OuterRef('pk'), type=TransactionTypeChoices.EXPENSE)
        .values('object_id')
        .annotate(
            total_uzs=Coalesce(
                Sum('amount', filter=Q(currency=CurrencyChoices.UZS)),
                ZERO,
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
            total_usd=Coalesce(
                Sum('amount', filter=Q(currency=CurrencyChoices.USD)),
                ZERO,
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
        )
    )
    return ConstructionObject.objects.annotate(
        total_expense_uzs=Coalesce(
            Subquery(
                expense_totals.values('total_uzs')[:1],
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
            ZERO,
        ),
        total_expense_usd=Coalesce(
            Subquery(
                expense_totals.values('total_usd')[:1],
                output_field=DecimalField(max_digits=18, decimal_places=2),
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
