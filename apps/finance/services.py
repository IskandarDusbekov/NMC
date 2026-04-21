from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.logs.services import AuditLogService

from .models import (
    CurrencyChoices,
    ExchangeRate,
    ManagerAccount,
    ManagerTransfer,
    Transaction,
    TransactionCategory,
    TransactionEntryTypeChoices,
    TransactionTypeChoices,
    WalletTypeChoices,
)


ZERO = Decimal('0.00')


class ExchangeRateService:
    @staticmethod
    def latest_rate():
        return ExchangeRate.objects.filter(is_active=True).order_by('-effective_at', '-created_at').first()

    @staticmethod
    def update_rate(*, usd_to_uzs, user):
        ExchangeRate.objects.update(is_active=False)
        return ExchangeRate.objects.create(usd_to_uzs=usd_to_uzs, updated_by=user, is_active=True)


class CompanyBalanceService:
    @staticmethod
    def _signed_total(queryset, currency: str) -> Decimal:
        total = ZERO
        for item in queryset.filter(currency=currency):
            total += item.amount * Decimal(item.sign)
        return total

    @classmethod
    def current_balance(cls, currency: str, queryset=None) -> Decimal:
        queryset = queryset if queryset is not None else Transaction.objects.company_wallet()
        return cls._signed_total(queryset, currency)

    @classmethod
    def summary(cls, queryset=None):
        queryset = queryset if queryset is not None else Transaction.objects.company_wallet()
        return {
            CurrencyChoices.UZS: cls.current_balance(CurrencyChoices.UZS, queryset),
            CurrencyChoices.USD: cls.current_balance(CurrencyChoices.USD, queryset),
        }


class ManagerBalanceService:
    @staticmethod
    def get_account_for_user(user):
        try:
            return user.manager_account
        except ManagerAccount.DoesNotExist as exc:
            raise ValidationError('Manager account topilmadi.') from exc

    @staticmethod
    def _signed_total(queryset, currency: str) -> Decimal:
        total = ZERO
        for item in queryset.filter(currency=currency):
            total += item.amount * Decimal(item.sign)
        return total

    @classmethod
    def current_balance(cls, manager_account, currency: str, queryset=None) -> Decimal:
        queryset = queryset if queryset is not None else Transaction.objects.manager_wallet().filter(manager_account=manager_account)
        return cls._signed_total(queryset, currency)

    @classmethod
    def summary_for_account(cls, manager_account):
        queryset = Transaction.objects.manager_wallet().filter(manager_account=manager_account)
        return {
            CurrencyChoices.UZS: cls.current_balance(manager_account, CurrencyChoices.UZS, queryset),
            CurrencyChoices.USD: cls.current_balance(manager_account, CurrencyChoices.USD, queryset),
        }

    @classmethod
    def total_manager_holdings(cls):
        queryset = Transaction.objects.manager_wallet()
        return {
            CurrencyChoices.UZS: cls._signed_total(queryset, CurrencyChoices.UZS),
            CurrencyChoices.USD: cls._signed_total(queryset, CurrencyChoices.USD),
        }


class TransactionService:
    @staticmethod
    def _prepare_payload(data):
        payload = data.copy()
        work_item = payload.get('work_item')
        if work_item and not payload.get('object'):
            payload['object'] = work_item.object
        payload.setdefault('wallet_type', WalletTypeChoices.COMPANY)
        if not payload.get('entry_type'):
            if payload['wallet_type'] == WalletTypeChoices.COMPANY and payload['type'] == TransactionTypeChoices.INCOME:
                payload['entry_type'] = TransactionEntryTypeChoices.COMPANY_INCOME
            elif payload['wallet_type'] == WalletTypeChoices.COMPANY and payload['type'] == TransactionTypeChoices.EXPENSE:
                payload['entry_type'] = TransactionEntryTypeChoices.COMPANY_EXPENSE
            elif payload['wallet_type'] == WalletTypeChoices.MANAGER and payload['type'] == TransactionTypeChoices.EXPENSE:
                payload['entry_type'] = TransactionEntryTypeChoices.MANAGER_EXPENSE
        return payload

    @staticmethod
    def _ensure_company_permissions(user):
        if user and not (getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}):
            raise ValidationError('Company hisobida faqat admin yoki director ishlay oladi.')

    @staticmethod
    def _ensure_manager_permissions(user, manager_account):
        if user is None:
            raise ValidationError('Manager amali uchun foydalanuvchi kerak.')
        if getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}:
            return
        if user.role != 'MANAGER':
            raise ValidationError('Manager hisobi bilan faqat manager yoki admin/director ishlay oladi.')
        if not manager_account or getattr(user, 'manager_account', None) != manager_account:
            raise ValidationError('Manager boshqa manager balansiga kira olmaydi.')

    @classmethod
    def _validate_balance(cls, payload, instance=None):
        draft = Transaction(**payload)
        queryset = Transaction.objects.active()
        if instance is not None:
            queryset = queryset.exclude(pk=instance.pk)

        if draft.wallet_type == WalletTypeChoices.COMPANY and draft.sign < 0:
            current_balance = CompanyBalanceService.current_balance(draft.currency, queryset.company_wallet())
            if draft.amount > current_balance:
                raise ValidationError({'amount': f'Company balans yetarli emas. Mavjud: {current_balance} {draft.currency}.'})

        if draft.wallet_type == WalletTypeChoices.MANAGER and draft.sign < 0:
            manager_queryset = queryset.manager_wallet().filter(manager_account=draft.manager_account)
            current_balance = ManagerBalanceService.current_balance(draft.manager_account, draft.currency, manager_queryset)
            if draft.amount > current_balance:
                raise ValidationError({'amount': f'Manager balans yetarli emas. Mavjud: {current_balance} {draft.currency}.'})

    @classmethod
    @db_transaction.atomic
    def create_transaction(cls, *, user=None, request=None, **data):
        payload = cls._prepare_payload(data)
        if payload['wallet_type'] == WalletTypeChoices.COMPANY:
            cls._ensure_company_permissions(user)
        if payload['wallet_type'] == WalletTypeChoices.MANAGER:
            cls._ensure_manager_permissions(user, payload.get('manager_account'))
        transaction = Transaction(created_by=user, **payload)
        transaction.full_clean()
        cls._validate_balance(payload)
        transaction.save()
        AuditLogService.log(
            user=user,
            action='transaction_created',
            model_name='Transaction',
            object_id=str(transaction.pk),
            description=f'{transaction.entry_type} - {transaction.amount} {transaction.currency}',
            ip_address=AuditLogService.get_ip_address(request) if request else None,
        )
        return transaction

    @classmethod
    @db_transaction.atomic
    def update_transaction(cls, instance, *, user=None, request=None, **data):
        payload = cls._prepare_payload(data)
        if payload['wallet_type'] == WalletTypeChoices.COMPANY:
            cls._ensure_company_permissions(user)
        if payload['wallet_type'] == WalletTypeChoices.MANAGER:
            cls._ensure_manager_permissions(user, payload.get('manager_account'))
        for field, value in payload.items():
            setattr(instance, field, value)
        instance.updated_by = user
        instance.full_clean()
        cls._validate_balance(payload, instance=instance)
        instance.save()
        AuditLogService.log(
            user=user,
            action='transaction_updated',
            model_name='Transaction',
            object_id=str(instance.pk),
            description=f'{instance.entry_type} transaction yangilandi.',
            ip_address=AuditLogService.get_ip_address(request) if request else None,
        )
        return instance

    @classmethod
    @db_transaction.atomic
    def soft_delete_transaction(cls, instance, *, user=None, request=None):
        if instance.is_deleted:
            return instance
        instance.is_deleted = True
        instance.deleted_by = user
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_by', 'deleted_at', 'updated_at'])
        AuditLogService.log(
            user=user,
            action='transaction_deleted',
            model_name='Transaction',
            object_id=str(instance.pk),
            description=f'{instance.entry_type} transaction soft delete qilindi.',
            ip_address=AuditLogService.get_ip_address(request) if request else None,
        )
        return instance

    @staticmethod
    def get_salary_category():
        category, _ = TransactionCategory.objects.get_or_create(
            name='Ish haqi',
            type=TransactionTypeChoices.EXPENSE,
            defaults={'description': 'Ishchilar maoshi', 'is_active': True},
        )
        return category


class TransferService:
    @staticmethod
    def _check_transfer_permissions(user, manager_account):
        if getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}:
            return
        if user.role == 'MANAGER' and getattr(user, 'manager_account', None) == manager_account:
            return
        raise ValidationError('Transfer amalini bajarish uchun ruxsat yo`q.')

    @classmethod
    @db_transaction.atomic
    def transfer_to_manager(cls, *, manager_account, amount, currency, description, date, user, request=None):
        if not (getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}):
            raise ValidationError('Managerga pul o`tkazish faqat admin/director uchun ruxsat etilgan.')
        company_balance = CompanyBalanceService.current_balance(currency)
        if amount > company_balance:
            raise ValidationError({'amount': f'Company balans yetarli emas. Mavjud: {company_balance} {currency}.'})

        transfer = ManagerTransfer.objects.create(
            from_user=user,
            to_manager=manager_account,
            amount=amount,
            currency=currency,
            description=description,
            date=date,
            transfer_kind=ManagerTransfer.TransferKind.TRANSFER,
        )
        TransactionService.create_transaction(
            user=user,
            request=request,
            type=TransactionTypeChoices.TRANSFER,
            entry_type=TransactionEntryTypeChoices.TRANSFER_TO_MANAGER,
            wallet_type=WalletTypeChoices.COMPANY,
            manager_account=manager_account,
            amount=amount,
            currency=currency,
            category=None,
            description=description or f'{manager_account} uchun transfer',
            date=date,
            object=None,
            work_item=None,
            worker=None,
            reference_type='manager_transfer',
            reference_id=str(transfer.pk),
            manager_transfer=transfer,
        )
        TransactionService.create_transaction(
            user=user,
            request=request,
            type=TransactionTypeChoices.TRANSFER,
            entry_type=TransactionEntryTypeChoices.TRANSFER_TO_MANAGER,
            wallet_type=WalletTypeChoices.MANAGER,
            manager_account=manager_account,
            amount=amount,
            currency=currency,
            category=None,
            description=description or f'Company hisobidan transfer',
            date=date,
            object=None,
            work_item=None,
            worker=None,
            reference_type='manager_transfer',
            reference_id=str(transfer.pk),
            manager_transfer=transfer,
        )
        AuditLogService.log(
            user=user,
            action='manager_transfer_created',
            model_name='ManagerTransfer',
            object_id=str(transfer.pk),
            description=f'{manager_account} ga {amount} {currency} o`tkazildi.',
            ip_address=AuditLogService.get_ip_address(request) if request else None,
        )
        return transfer

    @classmethod
    @db_transaction.atomic
    def return_to_company(cls, *, manager_account, amount, currency, description, date, user, request=None):
        cls._check_transfer_permissions(user, manager_account)
        manager_balance = ManagerBalanceService.current_balance(manager_account, currency)
        if amount > manager_balance:
            raise ValidationError({'amount': f'Manager balans yetarli emas. Mavjud: {manager_balance} {currency}.'})

        transfer = ManagerTransfer.objects.create(
            from_user=user,
            to_manager=manager_account,
            amount=amount,
            currency=currency,
            description=description,
            date=date,
            transfer_kind=ManagerTransfer.TransferKind.RETURN,
        )
        TransactionService.create_transaction(
            user=user,
            request=request,
            type=TransactionTypeChoices.TRANSFER,
            entry_type=TransactionEntryTypeChoices.MANAGER_RETURN,
            wallet_type=WalletTypeChoices.MANAGER,
            manager_account=manager_account,
            amount=amount,
            currency=currency,
            category=None,
            description=description or 'Qaytarilgan mablag`',
            date=date,
            object=None,
            work_item=None,
            worker=None,
            reference_type='manager_return',
            reference_id=str(transfer.pk),
            manager_transfer=transfer,
        )
        TransactionService.create_transaction(
            user=user,
            request=request,
            type=TransactionTypeChoices.TRANSFER,
            entry_type=TransactionEntryTypeChoices.MANAGER_RETURN,
            wallet_type=WalletTypeChoices.COMPANY,
            manager_account=manager_account,
            amount=amount,
            currency=currency,
            category=None,
            description=description or 'Manager qaytargan mablag`',
            date=date,
            object=None,
            work_item=None,
            worker=None,
            reference_type='manager_return',
            reference_id=str(transfer.pk),
            manager_transfer=transfer,
        )
        AuditLogService.log(
            user=user,
            action='manager_return_created',
            model_name='ManagerTransfer',
            object_id=str(transfer.pk),
            description=f'{manager_account} {amount} {currency} mablag`ni qaytardi.',
            ip_address=AuditLogService.get_ip_address(request) if request else None,
        )
        return transfer

    @staticmethod
    def today_transfer_count():
        return ManagerTransfer.objects.filter(
            date=timezone.now().date(),
            transfer_kind=ManagerTransfer.TransferKind.TRANSFER,
        ).count()


class ManagerExpenseService:
    @classmethod
    def create_expense(cls, *, manager_account, category, amount, currency, description, date, user, request=None, **extra):
        TransactionService._ensure_manager_permissions(user, manager_account)
        return TransactionService.create_transaction(
            user=user,
            request=request,
            type=TransactionTypeChoices.EXPENSE,
            entry_type=TransactionEntryTypeChoices.MANAGER_EXPENSE,
            wallet_type=WalletTypeChoices.MANAGER,
            manager_account=manager_account,
            amount=amount,
            currency=currency,
            category=category,
            description=description,
            date=date,
            **extra,
        )


class CompanyQuickActionService:
    @classmethod
    @db_transaction.atomic
    def execute(cls, *, user, request=None, action, amount, currency, category=None, manager_account=None, object=None, date=None, description=''):
        from apps.finance.forms import CompanyQuickActionForm

        if action == CompanyQuickActionForm.ACTION_COMPANY_INCOME:
            return TransactionService.create_transaction(
                user=user,
                request=request,
                type=TransactionTypeChoices.INCOME,
                wallet_type=WalletTypeChoices.COMPANY,
                manager_account=None,
                amount=amount,
                currency=currency,
                category=category,
                description=description,
                date=date,
                object=None,
                work_item=None,
                worker=None,
                reference_type='company_quick_action',
                reference_id='company-income',
            )

        if action == CompanyQuickActionForm.ACTION_COMPANY_EXPENSE:
            return TransactionService.create_transaction(
                user=user,
                request=request,
                type=TransactionTypeChoices.EXPENSE,
                wallet_type=WalletTypeChoices.COMPANY,
                manager_account=None,
                amount=amount,
                currency=currency,
                category=category,
                description=description,
                date=date,
                object=None,
                work_item=None,
                worker=None,
                reference_type='company_quick_action',
                reference_id='company-expense',
            )

        if action == CompanyQuickActionForm.ACTION_MANAGER_TRANSFER:
            if manager_account is None:
                raise ValidationError({'manager_account': 'Manager tanlang.'})
            return TransferService.transfer_to_manager(
                manager_account=manager_account,
                amount=amount,
                currency=currency,
                description=description,
                date=date,
                user=user,
                request=request,
            )

        if action == CompanyQuickActionForm.ACTION_OBJECT_FUNDING:
            if not (getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}):
                raise ValidationError('Obyektga mablag` yo`naltirish faqat admin/director uchun ruxsat etilgan.')
            if object is None:
                raise ValidationError({'object': 'Obyekt tanlang.'})

            company_balance = CompanyBalanceService.current_balance(currency)
            if amount > company_balance:
                raise ValidationError({'amount': f'Company balans yetarli emas. Mavjud: {company_balance} {currency}.'})

            transaction = TransactionService.create_transaction(
                user=user,
                request=request,
                type=TransactionTypeChoices.TRANSFER,
                entry_type=TransactionEntryTypeChoices.TRANSFER_TO_OBJECT,
                wallet_type=WalletTypeChoices.COMPANY,
                manager_account=None,
                amount=amount,
                currency=currency,
                category=None,
                description=description or f'{object.name} obyektiga mablag` yo`naltirildi',
                date=date,
                object=object,
                work_item=None,
                worker=None,
                reference_type='object_funding',
                reference_id=str(object.pk),
            )
            if currency == CurrencyChoices.UZS:
                object.balance_uzs += amount
                object.save(update_fields=['balance_uzs', 'updated_at'])
            else:
                object.balance_usd += amount
                object.save(update_fields=['balance_usd', 'updated_at'])
            AuditLogService.log(
                user=user,
                action='object_funded',
                model_name='ConstructionObject',
                object_id=str(object.pk),
                description=f'{object.name} obyektiga {amount} {currency} yo`naltirildi.',
                ip_address=AuditLogService.get_ip_address(request) if request else None,
            )
            return transaction

        if action == CompanyQuickActionForm.ACTION_OBJECT_RETURN:
            if not (getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}):
                raise ValidationError('Obyektdan mablag` chiqarish faqat admin/director uchun ruxsat etilgan.')
            if object is None:
                raise ValidationError({'object': 'Obyekt tanlang.'})

            object_balance = object.balance_uzs if currency == CurrencyChoices.UZS else object.balance_usd
            if amount > object_balance:
                raise ValidationError({'amount': f'Obyekt balansi yetarli emas. Mavjud: {object_balance} {currency}.'})

            transaction = TransactionService.create_transaction(
                user=user,
                request=request,
                type=TransactionTypeChoices.TRANSFER,
                entry_type=TransactionEntryTypeChoices.TRANSFER_FROM_OBJECT,
                wallet_type=WalletTypeChoices.COMPANY,
                manager_account=None,
                amount=amount,
                currency=currency,
                category=None,
                description=description or f'{object.name} obyektidan companyga qaytarildi',
                date=date,
                object=object,
                work_item=None,
                worker=None,
                reference_type='object_return',
                reference_id=str(object.pk),
            )
            if currency == CurrencyChoices.UZS:
                object.balance_uzs -= amount
                object.save(update_fields=['balance_uzs', 'updated_at'])
            else:
                object.balance_usd -= amount
                object.save(update_fields=['balance_usd', 'updated_at'])
            AuditLogService.log(
                user=user,
                action='object_funding_returned',
                model_name='ConstructionObject',
                object_id=str(object.pk),
                description=f'{object.name} obyektidan {amount} {currency} companyga qaytarildi.',
                ip_address=AuditLogService.get_ip_address(request) if request else None,
            )
            return transaction

        raise ValidationError({'action': 'Nomalum amal turi.'})
