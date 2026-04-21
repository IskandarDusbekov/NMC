from django.contrib import admin

from .models import ConstructionObject, WorkItem


class WorkItemInline(admin.TabularInline):
    model = WorkItem
    extra = 0


@admin.register(ConstructionObject)
class ConstructionObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'start_date', 'end_date', 'balance_uzs', 'balance_usd', 'budget_uzs', 'budget_usd')
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'address', 'description')
    inlines = [WorkItemInline]


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'object', 'assigned_worker', 'agreed_amount', 'currency', 'start_date', 'status')
    list_filter = ('status', 'currency', 'object', 'start_date')
    search_fields = ('title', 'description', 'assigned_worker__full_name', 'assigned_worker_group', 'object__name')
