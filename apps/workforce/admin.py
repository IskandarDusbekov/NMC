from django.contrib import admin

from .models import SalaryPayment, Worker


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'role_name', 'worker_type', 'monthly_salary', 'salary_currency', 'is_active')
    list_filter = ('worker_type', 'is_active', 'salary_currency')
    search_fields = ('full_name', 'phone', 'role_name')


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('date', 'worker', 'amount', 'currency', 'source_wallet', 'manager_account', 'object', 'created_by')
    list_filter = ('currency', 'date', 'object', 'source_wallet')
    search_fields = ('worker__full_name', 'description', 'object__name', 'manager_account__user__full_name')
    autocomplete_fields = ('worker', 'object', 'manager_account', 'created_by')
