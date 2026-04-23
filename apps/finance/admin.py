from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from .models import ExchangeRate, ExpenseItem, ManagerAccount, ManagerTransfer, MeasurementUnit, Transaction, TransactionCategory


def _money(value, currency=''):
    if value in (None, ''):
        return '-'
    formatted = f'{value:,.2f}'.replace(',', ' ')
    return f'{formatted} {currency}'.strip()


class ExpenseItemInline(admin.TabularInline):
    model = ExpenseItem
    extra = 1
    fields = ('name', 'default_unit', 'is_active', 'description')
    autocomplete_fields = ('default_unit',)
    show_change_link = True


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type_badge', 'detail_mode', 'active_badge', 'description')
    list_filter = ('type', 'detail_mode', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('type', 'name')
    list_editable = ('detail_mode',)
    list_per_page = 30

    def get_inlines(self, request, obj):
        if obj and obj.type == 'EXPENSE':
            return [ExpenseItemInline]
        return []

    @admin.display(description='Turi', ordering='type')
    def type_badge(self, obj):
        color = '#059669' if obj.type == 'INCOME' else '#dc2626'
        return format_html('<span style="color:{};font-weight:800;">{}</span>', color, obj.get_type_display())

    @admin.display(description='Faol', boolean=True, ordering='is_active')
    def active_badge(self, obj):
        return obj.is_active


@admin.register(MeasurementUnit)
class MeasurementUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'short_name')
    list_editable = ('short_name', 'is_active')
    list_per_page = 30


@admin.register(ExpenseItem)
class ExpenseItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'default_unit', 'is_active')
    list_filter = ('category', 'default_unit', 'is_active')
    search_fields = ('name', 'category__name', 'description')
    autocomplete_fields = ('category', 'default_unit')
    list_editable = ('default_unit', 'is_active')
    list_per_page = 30

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if request.GET.get('category'):
            initial['category'] = request.GET.get('category')
        return initial

    def response_add(self, request, obj, post_url_continue=None):
        response = super().response_add(request, obj, post_url_continue)
        if '_addanother' in request.POST and obj.category_id:
            add_url = reverse('admin:finance_expenseitem_add')
            return HttpResponseRedirect(f'{add_url}?category={obj.category_id}')
        return response


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('rate_display', 'effective_at', 'is_active', 'updated_by')
    list_filter = ('is_active', 'effective_at')
    search_fields = ('updated_by__username', 'updated_by__full_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'effective_at'

    @admin.display(description='USD kursi', ordering='usd_to_uzs')
    def rate_display(self, obj):
        return format_html('<b>1 USD = {} UZS</b>', _money(obj.usd_to_uzs))


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'wallet_badge', 'entry_type', 'item_name', 'amount_display', 'quantity_display', 'source', 'category', 'object', 'work_item', 'manager_account', 'receipt_link', 'deleted_badge')
    list_filter = ('wallet_type', 'entry_type', 'type', 'currency', 'source', 'category', 'is_deleted', 'date')
    search_fields = ('item_name', 'description', 'raw_text', 'reference_type', 'reference_id', 'object__name', 'worker__full_name', 'manager_account__user__full_name')
    autocomplete_fields = ('category', 'object', 'work_item', 'worker', 'manager_account', 'created_by', 'updated_by', 'deleted_by')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'receipt_link')
    date_hierarchy = 'date'
    list_per_page = 30

    @admin.display(description='Hisob', ordering='wallet_type')
    def wallet_badge(self, obj):
        colors = {'COMPANY': '#2563eb', 'MANAGER': '#d97706', 'OBJECT': '#7c3aed'}
        return format_html(
            '<span style="background:{};color:white;border-radius:999px;padding:4px 10px;font-weight:700;">{}</span>',
            colors.get(obj.wallet_type, '#64748b'),
            obj.get_wallet_type_display(),
        )

    @admin.display(description='Summa', ordering='amount')
    def amount_display(self, obj):
        color = '#dc2626' if obj.sign < 0 else '#059669'
        sign = '-' if obj.sign < 0 else '+'
        return format_html('<b style="color:{};">{}{}</b>', color, sign, _money(obj.amount, obj.currency))

    @admin.display(description='Miqdor / birlik')
    def quantity_display(self, obj):
        if not obj.quantity:
            return '-'
        unit_price = f' x {_money(obj.unit_price)}' if obj.unit_price else ''
        return f'{obj.quantity.normalize()} {obj.unit}{unit_price}'.strip()

    @admin.display(description='O`chirilgan', boolean=True, ordering='is_deleted')
    def deleted_badge(self, obj):
        return obj.is_deleted

    @admin.display(description='Chek')
    def receipt_link(self, obj):
        if not obj.receipt_file:
            return '-'
        return format_html('<a href="{}" target="_blank">Ko`rish</a>', obj.receipt_file.url)


@admin.register(ManagerAccount)
class ManagerAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_display', 'phone_display', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('user__full_name', 'user__username', 'user__phone')
    autocomplete_fields = ('user',)

    @admin.display(description='Role')
    def role_display(self, obj):
        return obj.user.get_role_display()

    @admin.display(description='Telefon')
    def phone_display(self, obj):
        return obj.user.phone or '-'


@admin.register(ManagerTransfer)
class ManagerTransferAdmin(admin.ModelAdmin):
    list_display = ('date', 'to_manager', 'amount_display', 'target_display', 'transfer_kind', 'from_user')
    list_filter = ('currency', 'transfer_kind', 'date')
    search_fields = ('to_manager__user__full_name', 'description', 'from_user__full_name')
    date_hierarchy = 'date'
    list_per_page = 30

    @admin.display(description='Summa', ordering='amount')
    def amount_display(self, obj):
        return _money(obj.amount, obj.currency)

    @admin.display(description='Aylantirilgan summa')
    def target_display(self, obj):
        if not obj.target_amount:
            return '-'
        return _money(obj.target_amount, obj.target_currency)
