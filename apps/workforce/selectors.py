from __future__ import annotations

from decimal import Decimal

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from apps.finance.models import CurrencyChoices

from .models import SalaryPayment, Worker


ZERO = Decimal('0.00')


def worker_queryset():
    return Worker.objects.annotate(
        total_paid_uzs=Coalesce(
            Sum('salary_payments__amount', filter=Q(salary_payments__currency=CurrencyChoices.UZS)),
            ZERO,
        ),
        total_paid_usd=Coalesce(
            Sum('salary_payments__amount', filter=Q(salary_payments__currency=CurrencyChoices.USD)),
            ZERO,
        ),
    )


def recent_salary_payments(limit=8, user=None):
    queryset = SalaryPayment.objects.select_related('worker', 'object', 'created_by', 'manager_account__user')
    if user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
        queryset = queryset.filter(manager_account=getattr(user, 'manager_account', None))
    return queryset[:limit]
