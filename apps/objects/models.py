from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel
from apps.finance.models import CurrencyChoices


class ConstructionObject(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        FINISHED = 'finished', 'Finished'

    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    balance_uzs = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    balance_usd = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    budget_uzs = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    budget_usd = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ('name',)

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'Yakun sanasi boshlanish sanasidan oldin bo`lishi mumkin emas.'})

    def __str__(self):
        return self.name


class WorkItem(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    object = models.ForeignKey(
        'objects.ConstructionObject',
        on_delete=models.CASCADE,
        related_name='work_items',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_worker = models.ForeignKey(
        'workforce.Worker',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='work_items',
    )
    assigned_worker_group = models.CharField(max_length=255, blank=True)
    agreed_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.UZS)
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    progress_percent = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('object__name', 'title')

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'Yakun sanasi boshlanish sanasidan oldin bo`lishi mumkin emas.'})
        if self.progress_percent < 0 or self.progress_percent > 100:
            raise ValidationError({'progress_percent': 'Progress 0 va 100 oralig`ida bo`lishi kerak.'})

    def __str__(self):
        return f'{self.object.name} - {self.title}'
