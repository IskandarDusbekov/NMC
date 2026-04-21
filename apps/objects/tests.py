from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import CurrencyChoices, TransactionCategory, TransactionTypeChoices
from apps.finance.services import TransactionService
from apps.workforce.models import Worker

from .models import ConstructionObject, WorkItem
from .selectors import work_item_queryset
from .services import ObjectAnalyticsService, ObjectFinanceService


User = get_user_model()


class ObjectAnalyticsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='manager2',
            password='test12345',
            full_name='Manager Two',
            role='DIRECTOR',
        )
        self.object = ConstructionObject.objects.create(
            name='Test Object',
            address='Tashkent',
            description='Demo',
            start_date=date(2026, 4, 1),
            budget_uzs=Decimal('5000000.00'),
        )
        self.income_category, _ = TransactionCategory.objects.get_or_create(
            name='Avans tushumi',
            type=TransactionTypeChoices.INCOME,
        )
        self.expense_category, _ = TransactionCategory.objects.get_or_create(
            name='Material',
            type=TransactionTypeChoices.EXPENSE,
        )
        TransactionService.create_transaction(
            user=self.user,
            type=TransactionTypeChoices.INCOME,
            amount=Decimal('5000000.00'),
            currency=CurrencyChoices.UZS,
            category=self.income_category,
            description='Capital',
            date=date(2026, 4, 2),
            object=None,
            work_item=None,
            worker=None,
            reference_type='manual',
            reference_id='cap-1',
        )
        TransactionService.create_transaction(
            user=self.user,
            type=TransactionTypeChoices.EXPENSE,
            amount=Decimal('1000000.00'),
            currency=CurrencyChoices.UZS,
            category=self.expense_category,
            description='Materials',
            date=date(2026, 4, 3),
            object=self.object,
            work_item=None,
            worker=None,
            reference_type='material',
            reference_id='mat-1',
        )

    def test_object_analytics_returns_expense_totals(self):
        analytics = ObjectAnalyticsService.analytics_for_object(self.object)
        self.assertEqual(analytics['total_expense_uzs'], Decimal('1000000.00'))
        self.assertEqual(analytics['remaining_budget_uzs'], Decimal('4000000.00'))

    def test_work_item_payment_can_use_different_currency(self):
        self.object.balance_usd = Decimal('1000.00')
        self.object.save(update_fields=['balance_usd', 'updated_at'])
        worker = Worker.objects.create(full_name='Brigada A')
        work_item = WorkItem.objects.create(
            object=self.object,
            title='Fasad',
            assigned_worker=worker,
            assigned_worker_group=worker.full_name,
            agreed_amount=Decimal('5000000.00'),
            currency=CurrencyChoices.UZS,
            start_date=date(2026, 4, 4),
        )

        ObjectFinanceService.create_work_item_payment(
            construction_object=self.object,
            user=self.user,
            worker=worker,
            work_item=work_item,
            amount=Decimal('100.00'),
            currency=CurrencyChoices.USD,
            date=date(2026, 4, 5),
            description='USD avans',
        )

        item = work_item_queryset().get(pk=work_item.pk)
        self.assertEqual(item.paid_amount_uzs, Decimal('0.00'))
        self.assertEqual(item.paid_amount_usd, Decimal('100.00'))
