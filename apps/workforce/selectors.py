from __future__ import annotations

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from apps.finance.models import CurrencyChoices, Transaction

from .models import SalaryPayment, Worker


ZERO = Decimal('0.00')


def worker_queryset():
    salary_totals = Transaction.objects.active().filter(
        worker_id=OuterRef('pk'),
        salary_payment__isnull=False,
    )
    return Worker.objects.annotate(
        total_paid_uzs=Coalesce(
            Subquery(
                salary_totals.filter(currency=CurrencyChoices.UZS)
                .values('worker')
                .annotate(total=Sum('amount'))
                .values('total')[:1],
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
            ZERO,
        ),
        total_paid_usd=Coalesce(
            Subquery(
                salary_totals.filter(currency=CurrencyChoices.USD)
                .values('worker')
                .annotate(total=Sum('amount'))
                .values('total')[:1],
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
            ZERO,
        ),
    )


def recent_salary_payments(limit=8, user=None):
    active_salary_payment_ids = Transaction.objects.active().filter(
        salary_payment__isnull=False,
    ).values_list('salary_payment_id', flat=True)
    queryset = SalaryPayment.objects.select_related('worker', 'object', 'created_by', 'manager_account__user').filter(
        pk__in=active_salary_payment_ids,
    )
    if user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
        queryset = queryset.filter(manager_account=getattr(user, 'manager_account', None))
    return queryset[:limit]
