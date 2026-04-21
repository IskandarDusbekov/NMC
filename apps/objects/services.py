from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.db.models import Avg, FloatField, Sum, Value
from django.db.models.functions import Coalesce

from apps.finance.models import CurrencyChoices, TransactionCategory, TransactionEntryTypeChoices, TransactionTypeChoices, WalletTypeChoices
from apps.finance.services import ManagerExpenseService, TransactionService

from .selectors import construction_object_queryset


ZERO = Decimal('0.00')
WORK_ITEM_PAYMENT_CATEGORY_NAME = 'Ish turi to`lovi'


class ObjectAnalyticsService:
    @staticmethod
    def analytics_for_object(construction_object):
        transactions = construction_object.transactions.active()
        work_items = construction_object.work_items.all()
        total_expense_uzs = transactions.filter(
            type=TransactionTypeChoices.EXPENSE,
            currency=CurrencyChoices.UZS,
        ).aggregate(total=Coalesce(Sum('amount'), ZERO))['total']
        total_expense_usd = transactions.filter(
            type=TransactionTypeChoices.EXPENSE,
            currency=CurrencyChoices.USD,
        ).aggregate(total=Coalesce(Sum('amount'), ZERO))['total']
        progress = work_items.aggregate(total=Coalesce(Avg('progress_percent'), Value(0.0), output_field=FloatField()))['total']
        return {
            'total_expense_uzs': total_expense_uzs,
            'total_expense_usd': total_expense_usd,
            'total_work_items': work_items.count(),
            'total_paid_uzs': total_expense_uzs,
            'total_paid_usd': total_expense_usd,
            'remaining_budget_uzs': (construction_object.budget_uzs or ZERO) - total_expense_uzs,
            'remaining_budget_usd': (construction_object.budget_usd or ZERO) - total_expense_usd,
            'progress': progress,
        }

    @staticmethod
    def top_expense_objects(limit=5):
        return construction_object_queryset().order_by('-total_expense_uzs', '-total_expense_usd')[:limit]

    @staticmethod
    def progress_objects(limit=5):
        return construction_object_queryset().order_by('-progress_average')[:limit]


class ObjectFinanceService:
    @staticmethod
    def get_work_item_payment_category():
        category, _ = TransactionCategory.objects.get_or_create(
            name=WORK_ITEM_PAYMENT_CATEGORY_NAME,
            type=TransactionTypeChoices.EXPENSE,
            defaults={
                'description': 'Obyekt ichidagi ish turlariga berilgan to`lovlar',
                'is_active': True,
            },
        )
        return category

    @staticmethod
    def _ensure_object_balance(construction_object, amount, currency):
        current_balance = construction_object.balance_uzs if currency == CurrencyChoices.UZS else construction_object.balance_usd
        if amount > current_balance:
            raise ValidationError({'amount': f'Obyekt balansi yetarli emas. Mavjud: {current_balance} {currency}.'})

    @staticmethod
    def _decrease_object_balance(construction_object, amount, currency):
        if currency == CurrencyChoices.UZS:
            construction_object.balance_uzs -= amount
            construction_object.save(update_fields=['balance_uzs', 'updated_at'])
            return
        construction_object.balance_usd -= amount
        construction_object.save(update_fields=['balance_usd', 'updated_at'])

    @staticmethod
    def _create_expense_transaction(*, user, request=None, manager_account=None, **payload):
        if getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
            manager_account = manager_account or getattr(user, 'manager_account', None)
            return ManagerExpenseService.create_expense(
                manager_account=manager_account,
                user=user,
                request=request,
                **payload,
            )
        construction_object = payload.get('object')
        amount = payload.get('amount')
        currency = payload.get('currency')
        ObjectFinanceService._ensure_object_balance(construction_object, amount, currency)
        transaction = TransactionService.create_transaction(
            user=user,
            request=request,
            type=TransactionTypeChoices.EXPENSE,
            entry_type=TransactionEntryTypeChoices.OBJECT_EXPENSE,
            wallet_type=WalletTypeChoices.OBJECT,
            manager_account=None,
            **payload,
        )
        ObjectFinanceService._decrease_object_balance(construction_object, amount, currency)
        return transaction

    @classmethod
    @db_transaction.atomic
    def create_work_item_payment(cls, *, construction_object, user, request=None, worker, work_item, amount, currency, date, description):
        category = cls.get_work_item_payment_category()
        return cls._create_expense_transaction(
            user=user,
            request=request,
            category=category,
            amount=amount,
            currency=currency,
            description=description or f'{work_item.title} uchun to`lov',
            date=date,
            object=construction_object,
            work_item=work_item,
            worker=worker,
            reference_type='object_work_item_payment',
            reference_id=f'object-{construction_object.pk}-work-item-{work_item.pk}',
        )

    @classmethod
    @db_transaction.atomic
    def create_object_expense(cls, *, construction_object, user, request=None, category, amount, currency, date, description):
        return cls._create_expense_transaction(
            user=user,
            request=request,
            category=category,
            amount=amount,
            currency=currency,
            description=description,
            date=date,
            object=construction_object,
            work_item=None,
            worker=None,
            reference_type='object_expense',
            reference_id=f'object-{construction_object.pk}',
        )

    @staticmethod
    def expense_summary_for_object(construction_object):
        rows = OrderedDict()
        transactions = construction_object.transactions.active().filter(
            type=TransactionTypeChoices.EXPENSE,
        ).select_related('category', 'work_item', 'worker')

        for transaction in transactions:
            if transaction.work_item_id:
                key = ('work_item', transaction.work_item_id)
                label = transaction.work_item.title
                row_type = 'Ish turi'
                work_item_id = transaction.work_item_id
                category_id = None
            else:
                key = ('category', transaction.category_id or 0)
                label = transaction.category.name if transaction.category else 'Boshqa xarajat'
                row_type = 'Xarajat'
                work_item_id = None
                category_id = transaction.category_id

            if key not in rows:
                rows[key] = {
                    'label': label,
                    'row_type': row_type,
                    'work_item_id': work_item_id,
                    'category_id': category_id,
                    'total_uzs': ZERO,
                    'total_usd': ZERO,
                    'count': 0,
                    'latest_date': transaction.date,
                }

            row = rows[key]
            if transaction.currency == CurrencyChoices.UZS:
                row['total_uzs'] += transaction.amount
            if transaction.currency == CurrencyChoices.USD:
                row['total_usd'] += transaction.amount
            row['count'] += 1
            if transaction.date and (not row['latest_date'] or transaction.date > row['latest_date']):
                row['latest_date'] = transaction.date

        return list(rows.values())
