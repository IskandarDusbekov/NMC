from django.contrib import admin
from django.utils.html import format_html

from .models import ConstructionObject, WorkItem


def _money(value, currency):
    return f'{value:,.2f} {currency}'.replace(',', ' ')


class WorkItemInline(admin.TabularInline):
    model = WorkItem
    extra = 0
    autocomplete_fields = ('assigned_worker',)
    fields = ('title', 'assigned_worker', 'agreed_amount', 'currency', 'status', 'start_date', 'end_date')


@admin.register(ConstructionObject)
class ConstructionObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'status_badge', 'start_date', 'end_date', 'balance_uzs_display', 'balance_usd_display')
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'address', 'description')
    inlines = [WorkItemInline]
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30

    @admin.display(description='Holat', ordering='status')
    def status_badge(self, obj):
        colors = {'active': '#059669', 'paused': '#d97706', 'finished': '#0f172a'}
        return format_html(
            '<span style="background:{};color:white;border-radius:999px;padding:4px 10px;font-weight:700;">{}</span>',
            colors.get(obj.status, '#64748b'),
            obj.get_status_display(),
        )

    @admin.display(description='Balans UZS', ordering='balance_uzs')
    def balance_uzs_display(self, obj):
        return _money(obj.balance_uzs, 'UZS')

    @admin.display(description='Balans USD', ordering='balance_usd')
    def balance_usd_display(self, obj):
        return _money(obj.balance_usd, 'USD')


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'object', 'assigned_worker', 'agreed_display', 'start_date', 'end_date', 'status_badge')
    list_filter = ('status', 'currency', 'object', 'start_date')
    search_fields = ('title', 'description', 'assigned_worker__full_name', 'assigned_worker_group', 'object__name')
    autocomplete_fields = ('object', 'assigned_worker')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30

    @admin.display(description='Kelishilgan summa', ordering='agreed_amount')
    def agreed_display(self, obj):
        return _money(obj.agreed_amount, obj.currency)

    @admin.display(description='Holat', ordering='status')
    def status_badge(self, obj):
        colors = {'planned': '#64748b', 'in_progress': '#2563eb', 'completed': '#059669', 'cancelled': '#dc2626'}
        return format_html(
            '<span style="background:{};color:white;border-radius:999px;padding:4px 10px;font-weight:700;">{}</span>',
            colors.get(obj.status, '#64748b'),
            obj.get_status_display(),
        )
