from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.objects.models import ConstructionObject

from .forms import CompanyQuickActionForm
from .models import CurrencyChoices, Transaction, TransactionCategory, TransactionTypeChoices
from .services import CompanyBalanceService, ManagerBalanceService, ManagerExpenseService, TransactionService, TransferService


User = get_user_model()


class TransactionServiceTest(TestCase):
    def setUp(self):
        self.director = User.objects.create_user(
            username='director',
            password='test12345',
            full_name='Director User',
            role='DIRECTOR',
        )
        self.manager = User.objects.create_user(
            username='manager',
            password='test12345',
            full_name='Manager User',
            role='MANAGER',
        )
        self.other_manager = User.objects.create_user(
            username='manager2',
            password='test12345',
            full_name='Manager Two',
            role='MANAGER',
        )
        self.income_category, _ = TransactionCategory.objects.get_or_create(
            name='Investor mablag`i',
            type=TransactionTypeChoices.INCOME,
        )
        self.expense_category, _ = TransactionCategory.objects.get_or_create(
            name='Material',
            type=TransactionTypeChoices.EXPENSE,
        )
        TransactionService.create_transaction(
            user=self.director,
            type=TransactionTypeChoices.INCOME,
            amount=Decimal('1000000.00'),
            currency=CurrencyChoices.UZS,
            category=self.income_category,
            description='Boshlang`ich kirim',
            date=date(2026, 4, 20),
            object=None,
            work_item=None,
            worker=None,
            reference_type='manual',
            reference_id='seed-1',
        )

    def test_transaction_create_updates_balance(self):
        balance = CompanyBalanceService.summary()
        self.assertEqual(balance[CurrencyChoices.UZS], Decimal('1000000.00'))

    def test_transfer_updates_company_and_manager_balances(self):
        TransferService.transfer_to_manager(
            manager_account=self.manager.manager_account,
            amount=Decimal('250000.00'),
            currency=CurrencyChoices.UZS,
            description='Transfer',
            date=date(2026, 4, 21),
            user=self.director,
        )

        company_balance = CompanyBalanceService.summary()
        manager_balance = ManagerBalanceService.summary_for_account(self.manager.manager_account)

        self.assertEqual(company_balance[CurrencyChoices.UZS], Decimal('750000.00'))
        self.assertEqual(manager_balance[CurrencyChoices.UZS], Decimal('250000.00'))

    def test_manager_expense_does_not_reduce_company_balance_twice(self):
        TransferService.transfer_to_manager(
            manager_account=self.manager.manager_account,
            amount=Decimal('300000.00'),
            currency=CurrencyChoices.UZS,
            description='Transfer',
            date=date(2026, 4, 21),
            user=self.director,
        )

        ManagerExpenseService.create_expense(
            manager_account=self.manager.manager_account,
            category=self.expense_category,
            amount=Decimal('100000.00'),
            currency=CurrencyChoices.UZS,
            description='Material xarajati',
            date=date(2026, 4, 22),
            object=None,
            work_item=None,
            worker=None,
            user=self.manager,
        )

        company_balance = CompanyBalanceService.summary()
        manager_balance = ManagerBalanceService.summary_for_account(self.manager.manager_account)

        self.assertEqual(company_balance[CurrencyChoices.UZS], Decimal('700000.00'))
        self.assertEqual(manager_balance[CurrencyChoices.UZS], Decimal('200000.00'))

    def test_manager_cannot_use_other_manager_account(self):
        TransferService.transfer_to_manager(
            manager_account=self.manager.manager_account,
            amount=Decimal('100000.00'),
            currency=CurrencyChoices.UZS,
            description='Transfer',
            date=date(2026, 4, 21),
            user=self.director,
        )

        with self.assertRaises(ValidationError):
            ManagerExpenseService.create_expense(
                manager_account=self.manager.manager_account,
                category=self.expense_category,
                amount=Decimal('10000.00'),
                currency=CurrencyChoices.UZS,
                description='No permission',
                date=date(2026, 4, 22),
                object=None,
                work_item=None,
                worker=None,
                user=self.other_manager,
            )


class FinancePermissionViewTest(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager-view',
            password='test12345',
            full_name='Manager View',
            role='MANAGER',
        )

    def test_manager_cannot_open_company_transaction_create_page(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('finance:transaction-create'))
        self.assertEqual(response.status_code, 403)


class FinanceQuickActionViewTest(TestCase):
    def setUp(self):
        self.director = User.objects.create_user(
            username='quick-director',
            password='test12345',
            full_name='Quick Director',
            role='DIRECTOR',
        )
        self.object = ConstructionObject.objects.create(
            name='Quick Object',
            address='Tashkent',
            start_date=date(2026, 4, 21),
        )
        self.client.force_login(self.director)

    def test_quick_income_creates_company_transaction_without_manual_category(self):
        response = self.client.post(
            reverse('finance:transaction-list'),
            {
                'action': CompanyQuickActionForm.ACTION_COMPANY_INCOME,
                'amount': '500000.00',
                'currency': CurrencyChoices.UZS,
                'date': '2026-04-21',
                'description': 'Quick income',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Transaction.objects.filter(description='Quick income').exists())
        self.assertEqual(CompanyBalanceService.current_balance(CurrencyChoices.UZS), Decimal('500000.00'))

    def test_quick_object_funding_and_return_update_balances(self):
        income_category, _ = TransactionCategory.objects.get_or_create(
            name='Boshqa kirim',
            type=TransactionTypeChoices.INCOME,
        )
        TransactionService.create_transaction(
            user=self.director,
            type=TransactionTypeChoices.INCOME,
            amount=Decimal('1000000.00'),
            currency=CurrencyChoices.UZS,
            category=income_category,
            description='Seed income',
            date=date(2026, 4, 21),
            object=None,
            work_item=None,
            worker=None,
            reference_type='test',
            reference_id='seed-income',
        )

        fund_response = self.client.post(
            reverse('finance:transaction-list'),
            {
                'action': CompanyQuickActionForm.ACTION_OBJECT_FUNDING,
                'amount': '200000.00',
                'currency': CurrencyChoices.UZS,
                'object': self.object.pk,
                'date': '2026-04-21',
                'description': 'Object funding',
            },
        )
        self.assertEqual(fund_response.status_code, 302)
        self.object.refresh_from_db()
        self.assertEqual(self.object.balance_uzs, Decimal('200000.00'))
        self.assertEqual(CompanyBalanceService.current_balance(CurrencyChoices.UZS), Decimal('800000.00'))

        return_response = self.client.post(
            reverse('finance:transaction-list'),
            {
                'action': CompanyQuickActionForm.ACTION_OBJECT_RETURN,
                'amount': '50000.00',
                'currency': CurrencyChoices.UZS,
                'object': self.object.pk,
                'date': '2026-04-21',
                'description': 'Object return',
            },
        )
        self.assertEqual(return_response.status_code, 302)
        self.object.refresh_from_db()
        self.assertEqual(self.object.balance_uzs, Decimal('150000.00'))
        self.assertEqual(CompanyBalanceService.current_balance(CurrencyChoices.UZS), Decimal('850000.00'))
