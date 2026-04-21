from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'model_name', 'object_id', 'user', 'ip_address')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('description', 'object_id', 'user__username', 'user__full_name')
    readonly_fields = ('created_at',)
