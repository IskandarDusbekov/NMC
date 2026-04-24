from django.contrib import admin
from django.utils.html import format_html

from .models import SalaryPayment, Worker


def _money(value, currency=''):
    if value in (None, ''):
        return '-'
    return f'{value:,.2f} {currency}'.replace(',', ' ').strip()


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'worker_type_badge', 'monthly_salary_display', 'total_paid_uzs', 'total_paid_usd', 'is_active')
    list_filter = ('worker_type', 'is_active', 'salary_currency')
    search_fields = ('full_name', 'phone', 'role_name')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30

    @admin.display(description='Turi', ordering='worker_type')
    def worker_type_badge(self, obj):
        color = '#2563eb' if obj.worker_type == 'monthly' else '#7c3aed'
        return format_html(
            '<span style="background:{};color:white;border-radius:999px;padding:4px 10px;font-weight:700;">{}</span>',
            color,
            obj.get_worker_type_display(),
        )

    @admin.display(description='Oylik maosh', ordering='monthly_salary')
    def monthly_salary_display(self, obj):
        if not obj.monthly_salary:
            return '-'
        return _money(obj.monthly_salary, obj.salary_currency)

    @admin.display(description='To`langan UZS')
    def total_paid_uzs(self, obj):
        return _money(
            sum(
                transaction.amount
                for transaction in obj.transactions.filter(currency='UZS', salary_payment__isnull=False, is_deleted=False)
            ),
            'UZS',
        )

    @admin.display(description='To`langan USD')
    def total_paid_usd(self, obj):
        return _money(
            sum(
                transaction.amount
                for transaction in obj.transactions.filter(currency='USD', salary_payment__isnull=False, is_deleted=False)
            ),
            'USD',
        )


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('date', 'worker', 'amount_display', 'source_wallet_badge', 'manager_account', 'object', 'receipt_link', 'created_by')
    list_filter = ('currency', 'date', 'object', 'source_wallet')
    search_fields = ('worker__full_name', 'description', 'object__name', 'manager_account__user__full_name')
    autocomplete_fields = ('worker', 'object', 'manager_account', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at', 'receipt_link')
    list_per_page = 30

    @admin.display(description='Summa', ordering='amount')
    def amount_display(self, obj):
        return _money(obj.amount, obj.currency)

    @admin.display(description='Manba', ordering='source_wallet')
    def source_wallet_badge(self, obj):
        colors = {'COMPANY': '#2563eb', 'MANAGER': '#d97706', 'OBJECT': '#7c3aed'}
        return format_html(
            '<span style="background:{};color:white;border-radius:999px;padding:4px 10px;font-weight:700;">{}</span>',
            colors.get(obj.source_wallet, '#64748b'),
            obj.get_source_wallet_display(),
        )

    @admin.display(description='Chek')
    def receipt_link(self, obj):
        if not obj.receipt_file:
            return '-'
        return format_html('<a href="{}" target="_blank">Ko`rish</a>', obj.receipt_file.url)
