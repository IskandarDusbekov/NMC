from django.contrib import admin

from .models import ExchangeRate, ExpenseItem, ManagerAccount, ManagerTransfer, MeasurementUnit, Transaction, TransactionCategory


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'detail_mode', 'is_active', 'description')
    list_filter = ('type', 'detail_mode', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('type', 'name')
    list_editable = ('detail_mode', 'is_active')


@admin.register(MeasurementUnit)
class MeasurementUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'short_name')
    list_editable = ('short_name', 'is_active')


@admin.register(ExpenseItem)
class ExpenseItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'default_unit', 'is_active')
    list_filter = ('category', 'default_unit', 'is_active')
    search_fields = ('name', 'category__name', 'description')
    autocomplete_fields = ('category', 'default_unit')
    list_editable = ('default_unit', 'is_active')


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('usd_to_uzs', 'effective_at', 'is_active', 'updated_by')
    list_filter = ('is_active', 'effective_at')
    search_fields = ('updated_by__username', 'updated_by__full_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'wallet_type', 'entry_type', 'item_name', 'amount', 'currency', 'quantity', 'unit', 'unit_price', 'source', 'category', 'object', 'is_deleted')
    list_filter = ('wallet_type', 'entry_type', 'type', 'currency', 'source', 'category', 'is_deleted', 'date')
    search_fields = ('item_name', 'description', 'raw_text', 'reference_type', 'reference_id', 'object__name', 'worker__full_name', 'manager_account__user__full_name')
    autocomplete_fields = ('category', 'object', 'work_item', 'worker', 'manager_account', 'created_by', 'updated_by', 'deleted_by')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    date_hierarchy = 'date'
    list_per_page = 30


@admin.register(ManagerAccount)
class ManagerAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('user__full_name', 'user__username', 'user__phone')
    autocomplete_fields = ('user',)


@admin.register(ManagerTransfer)
class ManagerTransferAdmin(admin.ModelAdmin):
    list_display = ('date', 'to_manager', 'amount', 'currency', 'transfer_kind', 'from_user')
    list_filter = ('currency', 'transfer_kind', 'date')
    search_fields = ('to_manager__user__full_name', 'description', 'from_user__full_name')
    date_hierarchy = 'date'
