from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteModel, TimeStampedModel


class CurrencyChoices(models.TextChoices):
    UZS = 'UZS', 'UZS'
    USD = 'USD', 'USD'


class TransactionTypeChoices(models.TextChoices):
    INCOME = 'INCOME', 'Income'
    EXPENSE = 'EXPENSE', 'Expense'
    TRANSFER = 'TRANSFER', 'Transfer'


class WalletTypeChoices(models.TextChoices):
    COMPANY = 'COMPANY', 'Ferma'
    MANAGER = 'MANAGER', 'Manager'
    OBJECT = 'OBJECT', 'Object'


class TransactionEntryTypeChoices(models.TextChoices):
    COMPANY_INCOME = 'COMPANY_INCOME', 'Ferma kirimi'
    COMPANY_EXPENSE = 'COMPANY_EXPENSE', 'Ferma chiqimi'
    TRANSFER_TO_MANAGER = 'TRANSFER_TO_MANAGER', 'Managerga o`tkazma'
    TRANSFER_TO_OBJECT = 'TRANSFER_TO_OBJECT', 'Obyektga o`tkazma'
    TRANSFER_FROM_OBJECT = 'TRANSFER_FROM_OBJECT', 'Obyektdan qaytarish'
    MANAGER_EXPENSE = 'MANAGER_EXPENSE', 'Manager xarajati'
    OBJECT_EXPENSE = 'OBJECT_EXPENSE', 'Obyekt xarajati'
    MANAGER_RETURN = 'MANAGER_RETURN', 'Manager qaytargan pul'
    MANAGER_TO_MANAGER = 'MANAGER_TO_MANAGER', 'Managerdan managerga'
    ADJUSTMENT = 'ADJUSTMENT', 'Tuzatish'


class TransactionCategory(TimeStampedModel):
    name = models.CharField(max_length=150)
    type = models.CharField(max_length=10, choices=TransactionTypeChoices.choices)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Kirim / xarajat turi'
        verbose_name_plural = 'Kirim / xarajat turlari'
        ordering = ('type', 'name')
        constraints = [
            models.UniqueConstraint(fields=('name', 'type'), name='unique_transaction_category_per_type'),
        ]

    def __str__(self):
        return f'{self.name} ({self.type})'


class ExchangeRate(TimeStampedModel):
    usd_to_uzs = models.DecimalField(max_digits=12, decimal_places=2)
    effective_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='exchange_rates_updated',
    )

    class Meta:
        ordering = ('-effective_at', '-created_at')

    def __str__(self):
        return f'1 USD = {self.usd_to_uzs} UZS'


class ManagerAccount(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='manager_account',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('user__full_name',)

    def clean(self):
        if self.user.role != 'MANAGER':
            raise ValidationError({'user': 'Manager account faqat MANAGER role dagi user uchun yaratiladi.'})

    def __str__(self):
        return self.user.full_name or self.user.username


class ManagerTransfer(TimeStampedModel):
    class TransferKind(models.TextChoices):
        TRANSFER = 'TRANSFER', 'Transfer'
        RETURN = 'RETURN', 'Return'

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='manager_transfers_sent',
    )
    to_manager = models.ForeignKey(
        'finance.ManagerAccount',
        on_delete=models.CASCADE,
        related_name='transfers',
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices)
    target_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    target_currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, blank=True)
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    description = models.TextField(blank=True)
    date = models.DateField(default=date.today)
    transfer_kind = models.CharField(max_length=20, choices=TransferKind.choices, default=TransferKind.TRANSFER)

    class Meta:
        ordering = ('-date', '-created_at')

    def __str__(self):
        return f'{self.to_manager} - {self.amount} {self.currency}'


class TransactionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

    def incomes(self):
        return self.active().filter(type=TransactionTypeChoices.INCOME)

    def expenses(self):
        return self.active().filter(type=TransactionTypeChoices.EXPENSE)

    def company_wallet(self):
        return self.active().filter(wallet_type=WalletTypeChoices.COMPANY)

    def manager_wallet(self):
        return self.active().filter(wallet_type=WalletTypeChoices.MANAGER)

    def object_wallet(self):
        return self.active().filter(wallet_type=WalletTypeChoices.OBJECT)


class Transaction(TimeStampedModel, SoftDeleteModel):
    type = models.CharField(max_length=10, choices=TransactionTypeChoices.choices)
    entry_type = models.CharField(max_length=40, choices=TransactionEntryTypeChoices.choices)
    wallet_type = models.CharField(max_length=20, choices=WalletTypeChoices.choices, default=WalletTypeChoices.COMPANY)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices)
    target_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    target_currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, blank=True)
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    category = models.ForeignKey(
        'finance.TransactionCategory',
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='transactions',
    )
    description = models.TextField(blank=True)
    date = models.DateField(default=date.today)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='transactions_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='transactions_updated',
    )
    object = models.ForeignKey(
        'objects.ConstructionObject',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
    )
    manager_account = models.ForeignKey(
        'finance.ManagerAccount',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
    )
    work_item = models.ForeignKey(
        'objects.WorkItem',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
    )
    worker = models.ForeignKey(
        'workforce.Worker',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
    )
    salary_payment = models.OneToOneField(
        'workforce.SalaryPayment',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='ledger_transaction',
    )
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=50, blank=True)
    manager_transfer = models.ForeignKey(
        'finance.ManagerTransfer',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='ledger_entries',
    )

    objects = TransactionQuerySet.as_manager()

    class Meta:
        ordering = ('-date', '-created_at')

    def clean(self):
        if self.type != TransactionTypeChoices.TRANSFER and not self.category:
            raise ValidationError({'category': 'Income va expense transactionlar uchun category majburiy.'})
        if self.type == TransactionTypeChoices.TRANSFER and self.category:
            raise ValidationError({'category': 'Ichki transferlar uchun category tanlanmaydi.'})
        if self.category and self.type != TransactionTypeChoices.TRANSFER and self.category.type != self.type:
            raise ValidationError({'category': 'Category turi transaction turi bilan mos bo`lishi kerak.'})
        if self.work_item and self.object_id and self.work_item.object_id != self.object_id:
            raise ValidationError({'work_item': 'Ish turi tanlangan obyektga tegishli emas.'})
        if self.work_item and not self.object_id:
            self.object = self.work_item.object
        if self.salary_payment and self.worker_id and self.salary_payment.worker_id != self.worker_id:
            raise ValidationError({'worker': 'Salary payment va transaction worker bir xil bo`lishi kerak.'})
        if self.wallet_type == WalletTypeChoices.MANAGER and not self.manager_account:
            raise ValidationError({'manager_account': 'Manager wallet transaction uchun manager account majburiy.'})
        if self.entry_type in {
            TransactionEntryTypeChoices.TRANSFER_TO_MANAGER,
            TransactionEntryTypeChoices.MANAGER_RETURN,
            TransactionEntryTypeChoices.MANAGER_TO_MANAGER,
        } and not self.manager_account:
            raise ValidationError({'manager_account': 'Transfer bilan bog`liq yozuvlarda manager account ko`rsatilishi kerak.'})

    def __str__(self):
        return f'{self.get_type_display()} {self.amount} {self.currency}'

    @property
    def sign(self):
        mapping = {
            (WalletTypeChoices.COMPANY, TransactionEntryTypeChoices.COMPANY_INCOME): 1,
            (WalletTypeChoices.COMPANY, TransactionEntryTypeChoices.COMPANY_EXPENSE): -1,
            (WalletTypeChoices.COMPANY, TransactionEntryTypeChoices.TRANSFER_TO_MANAGER): -1,
            (WalletTypeChoices.COMPANY, TransactionEntryTypeChoices.TRANSFER_TO_OBJECT): -1,
            (WalletTypeChoices.COMPANY, TransactionEntryTypeChoices.TRANSFER_FROM_OBJECT): 1,
            (WalletTypeChoices.COMPANY, TransactionEntryTypeChoices.MANAGER_RETURN): 1,
            (WalletTypeChoices.MANAGER, TransactionEntryTypeChoices.TRANSFER_TO_MANAGER): 1,
            (WalletTypeChoices.MANAGER, TransactionEntryTypeChoices.MANAGER_EXPENSE): -1,
            (WalletTypeChoices.MANAGER, TransactionEntryTypeChoices.MANAGER_RETURN): -1,
            (WalletTypeChoices.OBJECT, TransactionEntryTypeChoices.OBJECT_EXPENSE): -1,
        }
        if (self.wallet_type, self.entry_type) in mapping:
            return mapping[(self.wallet_type, self.entry_type)]
        return 1 if self.type == TransactionTypeChoices.INCOME else -1
