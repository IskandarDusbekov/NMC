from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.objects.models import ConstructionObject
from apps.objects.services import ObjectFinanceService

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

    def test_transfer_to_manager_can_convert_currency_and_delete_safely(self):
        usd_category, _ = TransactionCategory.objects.get_or_create(
            name='USD kirim',
            type=TransactionTypeChoices.INCOME,
        )
        TransactionService.create_transaction(
            user=self.director,
            type=TransactionTypeChoices.INCOME,
            amount=Decimal('100.00'),
            currency=CurrencyChoices.USD,
            category=usd_category,
            description='USD seed',
            date=date(2026, 4, 20),
            object=None,
            work_item=None,
            worker=None,
            reference_type='manual',
            reference_id='usd-seed',
        )

        transfer = TransferService.transfer_to_manager(
            manager_account=self.manager.manager_account,
            amount=Decimal('10.00'),
            currency=CurrencyChoices.USD,
            target_currency=CurrencyChoices.UZS,
            exchange_rate=Decimal('12000.00'),
            description='USD to UZS',
            date=date(2026, 4, 21),
            user=self.director,
        )

        self.assertEqual(CompanyBalanceService.current_balance(CurrencyChoices.USD), Decimal('90.00'))
        self.assertEqual(ManagerBalanceService.summary_for_account(self.manager.manager_account)[CurrencyChoices.UZS], Decimal('120000.00'))

        company_entry = Transaction.objects.get(manager_transfer=transfer, wallet_type='COMPANY')
        self.assertEqual(company_entry.target_amount, Decimal('120000.00'))
        self.assertEqual(company_entry.exchange_rate, Decimal('12000.00'))

        TransactionService.soft_delete_transaction(company_entry, user=self.director)

        self.assertEqual(CompanyBalanceService.current_balance(CurrencyChoices.USD), Decimal('100.00'))
        self.assertEqual(ManagerBalanceService.summary_for_account(self.manager.manager_account)[CurrencyChoices.UZS], Decimal('0.00'))

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

    def test_deleting_manager_transfer_soft_deletes_both_ledger_entries(self):
        transfer = TransferService.transfer_to_manager(
            manager_account=self.manager.manager_account,
            amount=Decimal('200000.00'),
            currency=CurrencyChoices.UZS,
            description='Transfer delete test',
            date=date(2026, 4, 21),
            user=self.director,
        )
        company_entry = Transaction.objects.get(manager_transfer=transfer, wallet_type='COMPANY')

        TransactionService.soft_delete_transaction(company_entry, user=self.director)

        self.assertFalse(Transaction.objects.active().filter(manager_transfer=transfer).exists())
        self.assertEqual(CompanyBalanceService.current_balance(CurrencyChoices.UZS), Decimal('1000000.00'))
        self.assertEqual(ManagerBalanceService.summary_for_account(self.manager.manager_account)[CurrencyChoices.UZS], Decimal('0.00'))

    def test_deleting_object_expense_restores_object_balance(self):
        construction_object = ConstructionObject.objects.create(
            name='Balance Object',
            address='Tashkent',
            start_date=date(2026, 4, 21),
            balance_uzs=Decimal('500000.00'),
        )
        transaction = ObjectFinanceService.create_object_expense(
            construction_object=construction_object,
            user=self.director,
            category=self.expense_category,
            amount=Decimal('100000.00'),
            currency=CurrencyChoices.UZS,
            date=date(2026, 4, 22),
            description='Elektr energiya',
        )
        construction_object.refresh_from_db()
        self.assertEqual(construction_object.balance_uzs, Decimal('400000.00'))

        TransactionService.soft_delete_transaction(transaction, user=self.director)

        construction_object.refresh_from_db()
        self.assertEqual(construction_object.balance_uzs, Decimal('500000.00'))

    def test_updating_object_expense_recalculates_object_balance(self):
        construction_object = ConstructionObject.objects.create(
            name='Edit Balance Object',
            address='Tashkent',
            start_date=date(2026, 4, 21),
            balance_uzs=Decimal('500000.00'),
        )
        transaction = ObjectFinanceService.create_object_expense(
            construction_object=construction_object,
            user=self.director,
            category=self.expense_category,
            amount=Decimal('100000.00'),
            currency=CurrencyChoices.UZS,
            date=date(2026, 4, 22),
            description='Elektr energiya',
        )

        TransactionService.update_transaction(
            transaction,
            user=self.director,
            type=TransactionTypeChoices.EXPENSE,
            entry_type=transaction.entry_type,
            wallet_type=transaction.wallet_type,
            manager_account=None,
            amount=Decimal('150000.00'),
            currency=CurrencyChoices.UZS,
            category=self.expense_category,
            description='Elektr energiya edit',
            date=date(2026, 4, 22),
            object=construction_object,
            work_item=None,
            worker=None,
            reference_type='object_expense',
            reference_id=f'object-{construction_object.pk}',
        )

        construction_object.refresh_from_db()
        self.assertEqual(construction_object.balance_uzs, Decimal('350000.00'))


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

    def test_quick_object_funding_can_convert_currency(self):
        income_category, _ = TransactionCategory.objects.get_or_create(
            name='USD kirim',
            type=TransactionTypeChoices.INCOME,
        )
        TransactionService.create_transaction(
            user=self.director,
            type=TransactionTypeChoices.INCOME,
            amount=Decimal('100.00'),
            currency=CurrencyChoices.USD,
            category=income_category,
            description='USD seed',
            date=date(2026, 4, 21),
            object=None,
            work_item=None,
            worker=None,
            reference_type='test',
            reference_id='usd-seed',
        )

        response = self.client.post(
            reverse('finance:transaction-list'),
            {
                'action': CompanyQuickActionForm.ACTION_OBJECT_FUNDING,
                'amount': '10.00',
                'currency': CurrencyChoices.USD,
                'target_currency': CurrencyChoices.UZS,
                'exchange_rate': '12000.00',
                'object': self.object.pk,
                'date': '2026-04-21',
                'description': 'Object funding convert',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.object.refresh_from_db()
        self.assertEqual(self.object.balance_uzs, Decimal('120000.00'))
        self.assertEqual(CompanyBalanceService.current_balance(CurrencyChoices.USD), Decimal('90.00'))

        transaction = Transaction.objects.get(description='Object funding convert')
        TransactionService.soft_delete_transaction(transaction, user=self.director)

        self.object.refresh_from_db()
        self.assertEqual(self.object.balance_uzs, Decimal('0.00'))
        self.assertEqual(CompanyBalanceService.current_balance(CurrencyChoices.USD), Decimal('100.00'))
