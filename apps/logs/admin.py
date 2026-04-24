from django.contrib import admin

from .models import AuditLog, BlockedIP


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'model_name', 'object_id', 'user', 'ip_address')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('description', 'object_id', 'user__username', 'user__full_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50


@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'failed_attempts', 'window_started_at', 'last_attempt_at', 'blocked_until', 'reason')
    search_fields = ('ip_address', 'reason')
    list_filter = ('blocked_until', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'last_attempt_at', 'window_started_at')
    list_per_page = 50
