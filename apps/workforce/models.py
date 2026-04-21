from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel
from apps.finance.models import CurrencyChoices, WalletTypeChoices


class Worker(TimeStampedModel):
    class WorkerType(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        BRIGADE = 'brigade', 'Brigade'

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    role_name = models.CharField(max_length=255, blank=True)
    worker_type = models.CharField(max_length=20, choices=WorkerType.choices, default=WorkerType.BRIGADE)
    monthly_salary = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    salary_currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('full_name',)

    def __str__(self):
        return self.full_name


class SalaryPayment(TimeStampedModel):
    worker = models.ForeignKey('workforce.Worker', on_delete=models.CASCADE, related_name='salary_payments')
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices)
    date = models.DateField(default=date.today)
    object = models.ForeignKey(
        'objects.ConstructionObject',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='salary_payments',
    )
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='salary_payments_created',
    )
    source_wallet = models.CharField(max_length=20, choices=WalletTypeChoices.choices, default=WalletTypeChoices.COMPANY)
    manager_account = models.ForeignKey(
        'finance.ManagerAccount',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='salary_payments',
    )

    class Meta:
        ordering = ('-date', '-created_at')

    def clean(self):
        if self.source_wallet == WalletTypeChoices.MANAGER and not self.manager_account:
            raise ValidationError({'manager_account': 'Manager wallet uchun manager hisobi majburiy.'})
        if self.source_wallet == WalletTypeChoices.COMPANY and self.manager_account:
            raise ValidationError({'manager_account': 'Company wallet tanlanganda manager hisobi bo`sh bo`lishi kerak.'})
        if self.source_wallet == WalletTypeChoices.OBJECT and not self.object:
            raise ValidationError({'object': 'Obyekt hisobidan to`lov uchun obyekt tanlang.'})
        if self.source_wallet == WalletTypeChoices.OBJECT and self.manager_account:
            raise ValidationError({'manager_account': 'Obyekt hisobidan to`lovda manager hisobi bo`sh bo`lishi kerak.'})

    def __str__(self):
        return f'{self.worker.full_name} - {self.amount} {self.currency}'
