from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.finance.models import CurrencyChoices, ManagerTransfer, Transaction, TransactionCategory, TransactionTypeChoices, WalletTypeChoices
from apps.finance.services import ExchangeRateService, ManagerExpenseService, TransactionService, TransferService
from apps.objects.models import ConstructionObject, WorkItem
from apps.workforce.models import Worker
from apps.workforce.services import SalaryPaymentService


class Command(BaseCommand):
    help = 'NMC demo ma`lumotlarini yaratadi: users, object, work item, transfer, expense va salary payment.'

    def handle(self, *args, **options):
        user_model = get_user_model()

        admin = self._get_or_create_user(
            user_model,
            username='admin_demo',
            full_name='Admin Demo',
            role='ADMIN',
            phone='+998900000001',
            telegram_id=910000001,
            telegram_username='nmc_admin_demo',
            is_staff=True,
        )
        director = self._get_or_create_user(
            user_model,
            username='director_demo',
            full_name='Director Demo',
            role='DIRECTOR',
            phone='+998900000002',
            telegram_id=910000002,
            telegram_username='nmc_director_demo',
        )
        manager = self._get_or_create_user(
            user_model,
            username='manager_demo',
            full_name='Manager Demo',
            role='MANAGER',
            phone='+998900000003',
            telegram_id=910000003,
            telegram_username='nmc_manager_demo',
        )
        self._get_or_create_user(
            user_model,
            username='manager_demo_2',
            full_name='Manager Demo 2',
            role='MANAGER',
            phone='+998900000004',
            telegram_id=910000004,
            telegram_username='nmc_manager_demo_2',
        )

        self._ensure_categories()
        ExchangeRateService.update_rate(usd_to_uzs=Decimal('12750.00'), user=admin)

        construction_object, _ = ConstructionObject.objects.get_or_create(
            name='Yunusobod Residence',
            defaults={
                'address': 'Toshkent shahri, Yunusobod tumani',
                'description': 'Demo premium residential object.',
                'status': ConstructionObject.Status.ACTIVE,
                'start_date': date(2026, 4, 1),
                'budget_uzs': Decimal('850000000.00'),
                'budget_usd': Decimal('50000.00'),
            },
        )
        worker, _ = Worker.objects.get_or_create(
            full_name='Sherzod Usta',
            defaults={
                'phone': '+998900000020',
                'role_name': 'Brigadir',
                'worker_type': Worker.WorkerType.MONTHLY,
                'monthly_salary': Decimal('6000000.00'),
                'salary_currency': CurrencyChoices.UZS,
                'notes': 'Demo salary worker.',
            },
        )
        work_item, _ = WorkItem.objects.get_or_create(
            object=construction_object,
            title='Fasad bo`yash',
            defaults={
                'description': 'Fasadni tozalash va bo`yash ishlari.',
                'assigned_worker': worker,
                'assigned_worker_group': worker.full_name,
                'agreed_amount': Decimal('18000000.00'),
                'currency': CurrencyChoices.UZS,
                'start_date': date(2026, 4, 3),
                'end_date': date(2026, 4, 25),
                'status': WorkItem.Status.IN_PROGRESS,
                'progress_percent': 48,
            },
        )
        if work_item.assigned_worker_id != worker.id or work_item.assigned_worker_group != worker.full_name:
            work_item.assigned_worker = worker
            work_item.assigned_worker_group = worker.full_name
            work_item.save(update_fields=['assigned_worker', 'assigned_worker_group', 'updated_at'])

        income_category = TransactionCategory.objects.get(name='Investor mablag`i', type=TransactionTypeChoices.INCOME)
        expense_category = TransactionCategory.objects.get(name='Material', type=TransactionTypeChoices.EXPENSE)

        if not Transaction.objects.filter(reference_type='seed', reference_id='company-income-uzs').exists():
            TransactionService.create_transaction(
                user=director,
                type=TransactionTypeChoices.INCOME,
                amount=Decimal('125000000.00'),
                currency=CurrencyChoices.UZS,
                category=income_category,
                description='Demo boshlang`ich company kirimi',
                date=date(2026, 4, 2),
                object=None,
                work_item=None,
                worker=None,
                reference_type='seed',
                reference_id='company-income-uzs',
            )

        if not Transaction.objects.filter(reference_type='seed', reference_id='company-income-usd').exists():
            TransactionService.create_transaction(
                user=director,
                type=TransactionTypeChoices.INCOME,
                amount=Decimal('18000.00'),
                currency=CurrencyChoices.USD,
                category=income_category,
                description='Demo USD company kirimi',
                date=date(2026, 4, 2),
                object=None,
                work_item=None,
                worker=None,
                reference_type='seed',
                reference_id='company-income-usd',
            )

        if not ManagerTransfer.objects.filter(description='Demo manager funding', transfer_kind=ManagerTransfer.TransferKind.TRANSFER).exists():
            TransferService.transfer_to_manager(
                manager_account=manager.manager_account,
                amount=Decimal('30000000.00'),
                currency=CurrencyChoices.UZS,
                description='Demo manager funding',
                date=date(2026, 4, 4),
                user=director,
            )

        if not Transaction.objects.filter(reference_type='seed', reference_id='manager-expense-material').exists():
            ManagerExpenseService.create_expense(
                manager_account=manager.manager_account,
                category=expense_category,
                amount=Decimal('8500000.00'),
                currency=CurrencyChoices.UZS,
                description='Demo material xarajati',
                date=date(2026, 4, 5),
                object=construction_object,
                work_item=work_item,
                worker=None,
                reference_type='seed',
                reference_id='manager-expense-material',
                user=manager,
            )

        if not Transaction.objects.filter(reference_type='seed', reference_id='salary-demo').exists():
            SalaryPaymentService.create_salary_payment(
                user=manager,
                worker=worker,
                amount=Decimal('3500000.00'),
                currency=CurrencyChoices.UZS,
                date=date(2026, 4, 6),
                source_wallet=WalletTypeChoices.MANAGER,
                manager_account=manager.manager_account,
                object=construction_object,
                description='Demo salary payment',
            )

        self.stdout.write(self.style.SUCCESS('Demo ma`lumotlar yaratildi yoki yangilandi.'))
        self.stdout.write('Telegram demo users:')
        self.stdout.write('  admin_demo / 910000001')
        self.stdout.write('  director_demo / 910000002')
        self.stdout.write('  manager_demo / 910000003')

    def _get_or_create_user(
        self,
        user_model,
        *,
        username: str,
        full_name: str,
        role: str,
        phone: str,
        telegram_id: int,
        telegram_username: str,
        is_staff: bool = False,
    ):
        defaults = {
            'full_name': full_name,
            'role': role,
            'phone': phone,
            'telegram_id': telegram_id,
            'telegram_username': telegram_username,
            'is_active': True,
            'is_staff': is_staff,
        }
        user, created = user_model.objects.get_or_create(username=username, defaults=defaults)
        changed = created
        for field, value in defaults.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed = True
        if created:
            user.set_unusable_password()
            changed = True
        if changed:
            user.save()
        return user

    def _ensure_categories(self):
        categories = [
            ('Investor mablag`i', TransactionTypeChoices.INCOME, 'Investor yoki owner mablag`i'),
            ('Buyurtmachidan tushum', TransactionTypeChoices.INCOME, 'Buyurtmachidan kelgan tushum'),
            ('Avans tushumi', TransactionTypeChoices.INCOME, 'Oldindan olingan to`lov'),
            ('Material', TransactionTypeChoices.EXPENSE, 'Material xarajatlari'),
            ('Transport', TransactionTypeChoices.EXPENSE, 'Transport va logistika'),
            ('Ish haqi', TransactionTypeChoices.EXPENSE, 'Salary va oylik to`lovlari'),
            ('Texnika', TransactionTypeChoices.EXPENSE, 'Texnika ijarasi yoki servisi'),
        ]
        for name, transaction_type, description in categories:
            TransactionCategory.objects.get_or_create(
                name=name,
                type=transaction_type,
                defaults={'description': description, 'is_active': True},
            )
