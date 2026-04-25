from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.urls import reverse

from apps.finance.models import CurrencyChoices, TransactionCategory, TransactionEntryTypeChoices, TransactionSourceChoices, TransactionTypeChoices, WalletTypeChoices
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
        work_item_paid_uzs = transactions.filter(
            type=TransactionTypeChoices.EXPENSE,
            currency=CurrencyChoices.UZS,
            work_item__isnull=False,
        ).aggregate(total=Coalesce(Sum('amount'), ZERO))['total']
        work_item_paid_usd = transactions.filter(
            type=TransactionTypeChoices.EXPENSE,
            currency=CurrencyChoices.USD,
            work_item__isnull=False,
        ).aggregate(total=Coalesce(Sum('amount'), ZERO))['total']
        other_expense_uzs = transactions.filter(
            type=TransactionTypeChoices.EXPENSE,
            currency=CurrencyChoices.UZS,
            work_item__isnull=True,
        ).aggregate(total=Coalesce(Sum('amount'), ZERO))['total']
        other_expense_usd = transactions.filter(
            type=TransactionTypeChoices.EXPENSE,
            currency=CurrencyChoices.USD,
            work_item__isnull=True,
        ).aggregate(total=Coalesce(Sum('amount'), ZERO))['total']
        total_work_items = work_items.count()
        completed_work_items = work_items.filter(status='completed').count()
        progress = (completed_work_items / total_work_items * 100) if total_work_items else 0
        return {
            'total_expense_uzs': total_expense_uzs,
            'total_expense_usd': total_expense_usd,
            'work_item_paid_uzs': work_item_paid_uzs,
            'work_item_paid_usd': work_item_paid_usd,
            'other_expense_uzs': other_expense_uzs,
            'other_expense_usd': other_expense_usd,
            'total_work_items': total_work_items,
            'completed_work_items': completed_work_items,
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
    def create_work_item_payment(cls, *, construction_object, user, request=None, worker, work_item, amount, currency, date, description, receipt_file=None):
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
            receipt_file=receipt_file,
            reference_type='object_work_item_payment',
            reference_id=f'object-{construction_object.pk}-work-item-{work_item.pk}',
        )

    @classmethod
    @db_transaction.atomic
    def create_object_expense(
        cls,
        *,
        construction_object,
        user,
        request=None,
        category,
        amount,
        currency,
        date,
        description,
        item_name='',
        quantity=None,
        unit='',
        unit_price=None,
        source=TransactionSourceChoices.MANUAL,
        raw_text='',
        receipt_file=None,
    ):
        return cls._create_expense_transaction(
            user=user,
            request=request,
            category=category,
            amount=amount,
            currency=currency,
            item_name=item_name,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            source=source,
            raw_text=raw_text,
            receipt_file=receipt_file,
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
            key = ('category', transaction.category_id or 0)
            label = transaction.category.name if transaction.category else 'Boshqa xarajat'
            row_type = transaction.category.get_detail_mode_display() if transaction.category else 'Xarajat'
            work_item_id = None
            category_id = transaction.category_id
            item_name = ''

            if key not in rows:
                rows[key] = {
                    'label': label,
                    'row_type': row_type,
                    'work_item_id': work_item_id,
                    'category_id': category_id,
                    'category_name': transaction.category.name if transaction.category else '',
                    'item_name': item_name,
                    'total_uzs': ZERO,
                    'total_usd': ZERO,
                    'quantity_totals': OrderedDict(),
                    'quantity_summary': '',
                    'count': 0,
                    'detail_count': 0,
                    'latest_date': transaction.date,
                    'has_receipt': False,
                }

            row = rows[key]
            if transaction.currency == CurrencyChoices.UZS:
                row['total_uzs'] += transaction.amount
            if transaction.currency == CurrencyChoices.USD:
                row['total_usd'] += transaction.amount
            row['count'] += 1
            if transaction.quantity or transaction.unit or transaction.unit_price:
                row['detail_count'] += 1
            if transaction.quantity and transaction.unit:
                row['quantity_totals'][transaction.unit] = row['quantity_totals'].get(transaction.unit, ZERO) + transaction.quantity
            if transaction.receipt_file:
                row['has_receipt'] = True
            if transaction.date and (not row['latest_date'] or transaction.date > row['latest_date']):
                row['latest_date'] = transaction.date

        for row in rows.values():
            row['quantity_summary'] = ', '.join(
                f'{amount.normalize()} {unit}' for unit, amount in row['quantity_totals'].items()
            )
        return list(rows.values())

    @staticmethod
    def expense_category_detail_for_object(construction_object, category):
        rows = OrderedDict()
        transactions = construction_object.transactions.active().filter(
            type=TransactionTypeChoices.EXPENSE,
            category=category,
        ).select_related('category', 'work_item', 'worker')

        for transaction in transactions:
            if transaction.work_item_id:
                key = ('work_item', transaction.work_item_id)
                label = transaction.work_item.title
                row_type = 'Ish turi'
            else:
                label = (transaction.item_name or '').strip() or category.name
                key = ('item', label.lower())
                row_type = 'Ichki tur' if transaction.item_name else 'Umumiy'

            if key not in rows:
                rows[key] = {
                    'label': label,
                    'row_type': row_type,
                    'total_uzs': ZERO,
                    'total_usd': ZERO,
                    'quantity_totals': OrderedDict(),
                    'quantity_summary': '',
                    'count': 0,
                    'latest_date': transaction.date,
                    'receipt_url': '',
                }

            row = rows[key]
            if transaction.currency == CurrencyChoices.UZS:
                row['total_uzs'] += transaction.amount
            if transaction.currency == CurrencyChoices.USD:
                row['total_usd'] += transaction.amount
            if transaction.quantity and transaction.unit:
                row['quantity_totals'][transaction.unit] = row['quantity_totals'].get(transaction.unit, ZERO) + transaction.quantity
            if transaction.receipt_file and not row['receipt_url']:
                row['receipt_url'] = reverse('finance:transaction-receipt', args=[transaction.pk])
            row['count'] += 1
            if transaction.date and (not row['latest_date'] or transaction.date > row['latest_date']):
                row['latest_date'] = transaction.date

        for row in rows.values():
            row['quantity_summary'] = ', '.join(
                f'{amount.normalize()} {unit}' for unit, amount in row['quantity_totals'].items()
            )

        return {
            'rows': list(rows.values()),
            'transactions': transactions,
        }
