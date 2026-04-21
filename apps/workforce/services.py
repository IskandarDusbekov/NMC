from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from apps.finance.models import TransactionEntryTypeChoices, TransactionTypeChoices, WalletTypeChoices
from apps.finance.services import ManagerExpenseService, TransactionService
from apps.logs.services import AuditLogService

from .models import SalaryPayment


class SalaryPaymentService:
    @staticmethod
    def _ensure_object_balance(construction_object, amount, currency):
        current_balance = construction_object.balance_uzs if currency == 'UZS' else construction_object.balance_usd
        if amount > current_balance:
            raise ValidationError({'amount': f'Obyekt balansi yetarli emas. Mavjud: {current_balance} {currency}.'})

    @staticmethod
    def _decrease_object_balance(construction_object, amount, currency):
        if currency == 'UZS':
            construction_object.balance_uzs -= amount
            construction_object.save(update_fields=['balance_uzs', 'updated_at'])
            return
        construction_object.balance_usd -= amount
        construction_object.save(update_fields=['balance_usd', 'updated_at'])

    @classmethod
    @db_transaction.atomic
    def create_salary_payment(cls, *, user=None, request=None, **data):
        payload = data.copy()
        if payload.get('source_wallet') == WalletTypeChoices.MANAGER and not payload.get('manager_account'):
            payload['manager_account'] = getattr(user, 'manager_account', None)

        salary_payment = SalaryPayment(created_by=user, **payload)
        salary_payment.full_clean()
        salary_payment.save()
        salary_category = TransactionService.get_salary_category()
        if salary_payment.source_wallet == WalletTypeChoices.MANAGER:
            manager_account = salary_payment.manager_account or getattr(user, 'manager_account', None)
            ManagerExpenseService.create_expense(
                manager_account=manager_account,
                category=salary_category,
                amount=salary_payment.amount,
                currency=salary_payment.currency,
                description=salary_payment.description or f'{salary_payment.worker.full_name} maoshi',
                date=salary_payment.date,
                object=salary_payment.object,
                work_item=None,
                worker=salary_payment.worker,
                salary_payment=salary_payment,
                reference_type='salary_payment',
                reference_id=str(salary_payment.pk),
                user=user,
                request=request,
            )
        elif salary_payment.source_wallet == WalletTypeChoices.OBJECT:
            cls._ensure_object_balance(salary_payment.object, salary_payment.amount, salary_payment.currency)
            TransactionService.create_transaction(
                user=user,
                request=request,
                type=TransactionTypeChoices.EXPENSE,
                entry_type=TransactionEntryTypeChoices.OBJECT_EXPENSE,
                wallet_type=WalletTypeChoices.OBJECT,
                manager_account=None,
                amount=salary_payment.amount,
                currency=salary_payment.currency,
                category=salary_category,
                description=salary_payment.description or f'{salary_payment.worker.full_name} maoshi',
                date=salary_payment.date,
                object=salary_payment.object,
                work_item=None,
                worker=salary_payment.worker,
                salary_payment=salary_payment,
                reference_type='salary_payment',
                reference_id=str(salary_payment.pk),
            )
            cls._decrease_object_balance(salary_payment.object, salary_payment.amount, salary_payment.currency)
        else:
            TransactionService.create_transaction(
                user=user,
                request=request,
                type=TransactionTypeChoices.EXPENSE,
                entry_type=TransactionEntryTypeChoices.COMPANY_EXPENSE,
                wallet_type=WalletTypeChoices.COMPANY,
                manager_account=None,
                amount=salary_payment.amount,
                currency=salary_payment.currency,
                category=salary_category,
                description=salary_payment.description or f'{salary_payment.worker.full_name} maoshi',
                date=salary_payment.date,
                object=salary_payment.object,
                work_item=None,
                worker=salary_payment.worker,
                salary_payment=salary_payment,
                reference_type='salary_payment',
                reference_id=str(salary_payment.pk),
            )
        AuditLogService.log(
            user=user,
            action='salary_payment_created',
            model_name='SalaryPayment',
            object_id=str(salary_payment.pk),
            description=f'{salary_payment.worker.full_name} uchun salary payment yaratildi.',
            ip_address=AuditLogService.get_ip_address(request) if request else None,
        )
        return salary_payment
