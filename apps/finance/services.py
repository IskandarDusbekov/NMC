from __future__ import annotations

import json
from datetime import datetime, time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.conf import settings
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
MONEY_QUANT = Decimal('0.01')


class ExchangeRateService:
    CBU_USD_ENDPOINT = 'https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/'

    @staticmethod
    def _date_is_today(value):
        if not value:
            return False
        if timezone.is_naive(value):
            value_date = value.date()
        else:
            value_date = timezone.localtime(value).date()
        return value_date == timezone.now().date()

    @classmethod
    def latest_rate(cls, *, auto_update=False, user=None):
        latest = ExchangeRate.objects.filter(is_active=True).order_by('-effective_at', '-created_at').first()
        if not auto_update:
            return latest
        if latest and cls._date_is_today(latest.created_at):
            return latest
        try:
            return cls.update_rate_from_cbu(user=user)
        except ValidationError:
            return latest

    @staticmethod
    def update_rate(*, usd_to_uzs, user, effective_at=None):
        ExchangeRate.objects.update(is_active=False)
        return ExchangeRate.objects.create(
            usd_to_uzs=usd_to_uzs,
            effective_at=effective_at or timezone.now(),
            updated_by=user,
            is_active=True,
        )

    @classmethod
    def fetch_cbu_usd_rate(cls, timeout=10):
        try:
            with urlopen(cls.CBU_USD_ENDPOINT, timeout=timeout) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise ValidationError(f'CBU kursini olishda xatolik: {exc}') from exc

        if not payload:
            raise ValidationError('CBU API bo`sh javob qaytardi.')
        row = payload[0]
        try:
            rate = Decimal(str(row.get('Rate', '')).replace(',', '.'))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError('CBU API kurs qiymatini noto`g`ri formatda qaytardi.') from exc
        effective_at = timezone.now()
        date_value = row.get('Date')
        if date_value:
            try:
                parsed_date = datetime.strptime(date_value, '%d.%m.%Y').date()
                effective_at = datetime.combine(parsed_date, time.min)
                if settings.USE_TZ:
                    effective_at = timezone.make_aware(effective_at)
            except ValueError:
                effective_at = timezone.now()
        return rate, effective_at

    @classmethod
    def update_rate_from_cbu(cls, *, user):
        rate, effective_at = cls.fetch_cbu_usd_rate()
        return cls.update_rate(usd_to_uzs=rate, effective_at=effective_at, user=user)


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
    def _money(value):
        return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    @staticmethod
    def _object_balance_delta(transaction):
        if not transaction.object_id:
            return None
        amount = transaction.target_amount if transaction.target_amount is not None else transaction.amount
        currency = transaction.target_currency or transaction.currency
        mapping = {
            (WalletTypeChoices.OBJECT, TransactionEntryTypeChoices.OBJECT_EXPENSE): amount,
            (WalletTypeChoices.COMPANY, TransactionEntryTypeChoices.TRANSFER_TO_OBJECT): -amount,
            (WalletTypeChoices.COMPANY, TransactionEntryTypeChoices.TRANSFER_FROM_OBJECT): amount,
        }
        delta = mapping.get((transaction.wallet_type, transaction.entry_type))
        if delta is None:
            return None
        return currency, delta

    @classmethod
    def _apply_object_balance_delta(cls, transaction, multiplier=1):
        result = cls._object_balance_delta(transaction)
        if not result:
            return
        currency, delta = result
        construction_object = transaction.object
        construction_object.refresh_from_db(fields=['balance_uzs', 'balance_usd', 'updated_at'])
        signed_delta = delta * Decimal(multiplier)
        if currency == CurrencyChoices.UZS:
            next_balance = construction_object.balance_uzs + signed_delta
            if next_balance < 0:
                raise ValidationError({'amount': f'Obyekt UZS balansi manfiyga tushib ketadi: {next_balance} UZS.'})
            construction_object.balance_uzs = next_balance
            construction_object.save(update_fields=['balance_uzs', 'updated_at'])
            return
        next_balance = construction_object.balance_usd + signed_delta
        if next_balance < 0:
            raise ValidationError({'amount': f'Obyekt USD balansi manfiyga tushib ketadi: {next_balance} USD.'})
        construction_object.balance_usd = next_balance
        construction_object.save(update_fields=['balance_usd', 'updated_at'])

    @classmethod
    def _validate_soft_delete_balances(cls, transactions):
        company_deltas: dict[str, Decimal] = {}
        manager_deltas: dict[tuple[int, str], Decimal] = {}

        for transaction in transactions:
            signed_amount = transaction.amount * Decimal(transaction.sign)
            if transaction.wallet_type == WalletTypeChoices.COMPANY:
                company_deltas[transaction.currency] = company_deltas.get(transaction.currency, ZERO) + signed_amount
            if transaction.wallet_type == WalletTypeChoices.MANAGER and transaction.manager_account_id:
                key = (transaction.manager_account_id, transaction.currency)
                manager_deltas[key] = manager_deltas.get(key, ZERO) + signed_amount

        company_queryset = Transaction.objects.company_wallet()
        for currency, delta in company_deltas.items():
            next_balance = CompanyBalanceService.current_balance(currency, company_queryset) - delta
            if next_balance < 0:
                raise ValidationError(
                    {'__all__': f'Bu yozuvni o`chirishdan keyin ferma balansi manfiy bo`lib qoladi: {next_balance} {currency}.'}
                )

        for (manager_account_id, currency), delta in manager_deltas.items():
            manager_queryset = Transaction.objects.manager_wallet().filter(manager_account_id=manager_account_id)
            manager_account = ManagerAccount.objects.get(pk=manager_account_id)
            next_balance = ManagerBalanceService.current_balance(manager_account, currency, manager_queryset) - delta
            if next_balance < 0:
                manager_name = getattr(manager_account.user, 'full_name', '') or getattr(manager_account.user, 'username', '')
                raise ValidationError(
                    {'__all__': f'Bu yozuvni o`chirishdan keyin {manager_name} manager balansida manfiy qoldiq chiqadi: {next_balance} {currency}.'}
                )

    @classmethod
    def _transfer_group_queryset(cls, instance):
        if instance.manager_transfer_id:
            return Transaction.objects.active().filter(manager_transfer=instance.manager_transfer)
        if instance.reference_type in {'manager_transfer', 'manager_return'} and instance.reference_id:
            return Transaction.objects.active().filter(
                reference_type=instance.reference_type,
                reference_id=instance.reference_id,
            )
        return Transaction.objects.active().filter(pk=instance.pk)

    @staticmethod
    def _resolve_instance(instance):
        if instance is None:
            raise ValidationError('Transaction topilmadi.')
        if getattr(instance, 'pk', None):
            resolved = Transaction.objects.filter(pk=instance.pk).first()
            if resolved is not None:
                return resolved
        salary_payment = getattr(instance, 'salary_payment', None)
        if salary_payment is not None:
            resolved = Transaction.objects.filter(salary_payment=salary_payment).first()
            if resolved is not None:
                return resolved
        raise ValidationError('Transaction topilmadi yoki allaqachon ochirilgan.')

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
        original = Transaction.objects.select_related('object').get(pk=instance.pk)
        payload = cls._prepare_payload(data)
        if payload['wallet_type'] == WalletTypeChoices.COMPANY:
            cls._ensure_company_permissions(user)
        if payload['wallet_type'] == WalletTypeChoices.MANAGER:
            cls._ensure_manager_permissions(user, payload.get('manager_account'))
        cls._apply_object_balance_delta(original, multiplier=1)
        for field, value in payload.items():
            setattr(instance, field, value)
        instance.updated_by = user
        try:
            instance.full_clean()
            cls._validate_balance(payload, instance=instance)
            cls._apply_object_balance_delta(instance, multiplier=-1)
            instance.save()
        except Exception:
            cls._apply_object_balance_delta(original, multiplier=-1)
            raise
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
        instance = cls._resolve_instance(instance)
        if instance.is_deleted:
            return instance
        transactions = list(cls._transfer_group_queryset(instance).select_related('object', 'manager_transfer'))
        cls._validate_soft_delete_balances(transactions)
        deleted_at = timezone.now()
        for transaction in transactions:
            cls._apply_object_balance_delta(transaction, multiplier=1)
            Transaction.objects.filter(pk=transaction.pk).update(
                is_deleted=True,
                deleted_by=user,
                deleted_at=deleted_at,
                updated_at=deleted_at,
            )
        AuditLogService.log(
            user=user,
            action='transaction_deleted',
            model_name='Transaction',
            object_id=str(instance.pk),
            description=f'{instance.entry_type} transaction soft delete qilindi. Bog`liq yozuvlar: {len(transactions)}.',
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
    def _resolve_conversion(*, amount, currency, target_currency=None, exchange_rate=None):
        target_currency = target_currency or currency
        if target_currency == currency:
            return amount, target_currency, None

        if exchange_rate in (None, ''):
            latest_rate = ExchangeRateService.latest_rate(auto_update=True, user=None)
            if latest_rate is None:
                latest_rate = ExchangeRateService.update_rate_from_cbu(user=None)
            exchange_rate = latest_rate.usd_to_uzs

        exchange_rate = Decimal(exchange_rate)
        if exchange_rate <= 0:
            raise ValidationError({'exchange_rate': 'Kurs 0 dan katta bo`lishi kerak.'})
        if currency == CurrencyChoices.USD and target_currency == CurrencyChoices.UZS:
            return TransactionService._money(amount * exchange_rate), target_currency, exchange_rate
        if currency == CurrencyChoices.UZS and target_currency == CurrencyChoices.USD:
            return TransactionService._money(amount / exchange_rate), target_currency, exchange_rate
        raise ValidationError({'target_currency': 'Valyuta aylantirish faqat USD <-> UZS uchun ishlaydi.'})

    @staticmethod
    def _check_transfer_permissions(user, manager_account):
        if getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}:
            return
        if user.role == 'MANAGER' and getattr(user, 'manager_account', None) == manager_account:
            return
        raise ValidationError('Transfer amalini bajarish uchun ruxsat yo`q.')

    @classmethod
    @db_transaction.atomic
    def transfer_to_manager(cls, *, manager_account, amount, currency, description, date, user, request=None, target_currency=None, exchange_rate=None):
        if not (getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}):
            raise ValidationError('Managerga pul o`tkazish faqat admin/director uchun ruxsat etilgan.')
        company_balance = CompanyBalanceService.current_balance(currency)
        if amount > company_balance:
            raise ValidationError({'amount': f'Ferma balansi yetarli emas. Mavjud: {company_balance} {currency}.'})
        target_amount, target_currency, exchange_rate = cls._resolve_conversion(
            amount=amount,
            currency=currency,
            target_currency=target_currency,
            exchange_rate=exchange_rate,
        )

        transfer = ManagerTransfer.objects.create(
            from_user=user,
            to_manager=manager_account,
            amount=amount,
            currency=currency,
            target_amount=target_amount,
            target_currency=target_currency,
            exchange_rate=exchange_rate,
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
            target_amount=target_amount,
            target_currency=target_currency,
            exchange_rate=exchange_rate,
            category=None,
            description=description or f'{manager_account} uchun o`tkazma',
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
            amount=target_amount,
            currency=target_currency,
            target_amount=amount,
            target_currency=currency,
            exchange_rate=exchange_rate,
            category=None,
            description=description or f'Ferma hisobidan o`tkazma',
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
            description=f'{manager_account} ga {amount} {currency} -> {target_amount} {target_currency} o`tkazildi.',
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
    def execute(cls, *, user, request=None, action, amount, currency, category=None, manager_account=None, object=None, date=None, description='', target_currency=None, exchange_rate=None):
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
                target_currency=target_currency,
                exchange_rate=exchange_rate,
            )

        if action == CompanyQuickActionForm.ACTION_OBJECT_FUNDING:
            if not (getattr(user, 'is_superuser', False) or user.role in {'ADMIN', 'DIRECTOR'}):
                raise ValidationError('Obyektga mablag` yo`naltirish faqat admin/director uchun ruxsat etilgan.')
            if object is None:
                raise ValidationError({'object': 'Obyekt tanlang.'})

            company_balance = CompanyBalanceService.current_balance(currency)
            if amount > company_balance:
                raise ValidationError({'amount': f'Ferma balansi yetarli emas. Mavjud: {company_balance} {currency}.'})
            target_amount, target_currency, exchange_rate = TransferService._resolve_conversion(
                amount=amount,
                currency=currency,
                target_currency=target_currency,
                exchange_rate=exchange_rate,
            )

            transaction = TransactionService.create_transaction(
                user=user,
                request=request,
                type=TransactionTypeChoices.TRANSFER,
                entry_type=TransactionEntryTypeChoices.TRANSFER_TO_OBJECT,
                wallet_type=WalletTypeChoices.COMPANY,
                manager_account=None,
                amount=amount,
                currency=currency,
                target_amount=target_amount,
                target_currency=target_currency,
                exchange_rate=exchange_rate,
                category=None,
                description=description or f'{object.name} obyektiga mablag` yo`naltirildi',
                date=date,
                object=object,
                work_item=None,
                worker=None,
                reference_type='object_funding',
                reference_id=str(object.pk),
            )
            if target_currency == CurrencyChoices.UZS:
                object.balance_uzs += target_amount
                object.save(update_fields=['balance_uzs', 'updated_at'])
            else:
                object.balance_usd += target_amount
                object.save(update_fields=['balance_usd', 'updated_at'])
            AuditLogService.log(
                user=user,
                action='object_funded',
                model_name='ConstructionObject',
                object_id=str(object.pk),
                description=f'{object.name} obyektiga {amount} {currency} -> {target_amount} {target_currency} yo`naltirildi.',
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
