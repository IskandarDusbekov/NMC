from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import CurrencyChoices, TransactionCategory, TransactionTypeChoices, WalletTypeChoices
from apps.finance.services import CompanyBalanceService, ManagerBalanceService, TransactionService, TransferService

from .models import Worker
from .selectors import recent_salary_payments, worker_queryset
from .services import SalaryPaymentService


User = get_user_model()


class SalaryPaymentServiceTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='salary-admin',
            password='test12345',
            full_name='Salary Admin',
            role='ADMIN',
        )
        self.manager = User.objects.create_user(
            username='salary-manager',
            password='test12345',
            full_name='Salary Manager',
            role='MANAGER',
        )
        self.worker = Worker.objects.create(full_name='Worker A', worker_type='monthly', monthly_salary=Decimal('1000.00'))
        self.income_category, _ = TransactionCategory.objects.get_or_create(
            name='Investor mablag`i',
            type=TransactionTypeChoices.INCOME,
        )
        TransactionService.create_transaction(
            user=self.admin,
            type=TransactionTypeChoices.INCOME,
            amount=Decimal('10000.00'),
            currency=CurrencyChoices.USD,
            category=self.income_category,
            description='Funding',
            date=date(2026, 4, 20),
            object=None,
            work_item=None,
            worker=None,
            reference_type='manual',
            reference_id='fund-1',
        )

    def test_salary_payment_creates_transaction(self):
        salary_payment = SalaryPaymentService.create_salary_payment(
            user=self.admin,
            worker=self.worker,
            amount=Decimal('500.00'),
            currency=CurrencyChoices.USD,
            date=date(2026, 4, 20),
            source_wallet=WalletTypeChoices.COMPANY,
            manager_account=None,
            object=None,
            description='Monthly salary',
        )
        self.assertIsNotNone(salary_payment.ledger_transaction)
        self.assertEqual(salary_payment.ledger_transaction.worker, self.worker)

    def test_manager_wallet_salary_payment_assigns_manager_account(self):
        TransferService.transfer_to_manager(
            manager_account=self.manager.manager_account,
            amount=Decimal('2000.00'),
            currency=CurrencyChoices.USD,
            description='Manager funding',
            date=date(2026, 4, 21),
            user=self.admin,
        )

        salary_payment = SalaryPaymentService.create_salary_payment(
            user=self.manager,
            worker=self.worker,
            amount=Decimal('400.00'),
            currency=CurrencyChoices.USD,
            date=date(2026, 4, 22),
            source_wallet=WalletTypeChoices.MANAGER,
            manager_account=None,
            object=None,
            description='Manager wallet salary',
        )

        manager_balance = ManagerBalanceService.summary_for_account(self.manager.manager_account)
        company_balance = CompanyBalanceService.summary()

        self.assertEqual(salary_payment.manager_account, self.manager.manager_account)
        self.assertEqual(salary_payment.ledger_transaction.wallet_type, WalletTypeChoices.MANAGER)
        self.assertEqual(manager_balance[CurrencyChoices.USD], Decimal('1600.00'))
        self.assertEqual(company_balance[CurrencyChoices.USD], Decimal('8000.00'))

    def test_deleted_salary_payment_is_excluded_from_worker_totals_and_recent_list(self):
        salary_payment = SalaryPaymentService.create_salary_payment(
            user=self.admin,
            worker=self.worker,
            amount=Decimal('500.00'),
            currency=CurrencyChoices.USD,
            date=date(2026, 4, 20),
            source_wallet=WalletTypeChoices.COMPANY,
            manager_account=None,
            object=None,
            description='Monthly salary',
        )

        TransactionService.soft_delete_transaction(salary_payment.ledger_transaction, user=self.admin)

        worker = worker_queryset().get(pk=self.worker.pk)
        self.assertEqual(worker.total_paid_usd, Decimal('0.00'))
        self.assertEqual(list(recent_salary_payments(user=self.admin)), [])
