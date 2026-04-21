from django.contrib import admin

from .models import ConstructionObject, WorkItem


class WorkItemInline(admin.TabularInline):
    model = WorkItem
    extra = 0
    autocomplete_fields = ('assigned_worker',)
    fields = ('title', 'assigned_worker', 'agreed_amount', 'currency', 'status', 'start_date', 'end_date')


@admin.register(ConstructionObject)
class ConstructionObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'status', 'start_date', 'end_date', 'balance_uzs', 'balance_usd')
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'address', 'description')
    inlines = [WorkItemInline]
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'object', 'assigned_worker', 'agreed_amount', 'currency', 'start_date', 'status')
    list_filter = ('status', 'currency', 'object', 'start_date')
    search_fields = ('title', 'description', 'assigned_worker__full_name', 'assigned_worker_group', 'object__name')
    autocomplete_fields = ('object', 'assigned_worker')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')
