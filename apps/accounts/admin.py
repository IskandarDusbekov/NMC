from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import AccessToken, TelegramBotState, TelegramLoginSession, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'full_name', 'role_badge', 'phone', 'telegram_id', 'telegram_username', 'active_badge', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'full_name', 'phone', 'telegram_username', 'telegram_id')
    ordering = ('username',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Qo`shimcha ma`lumotlar', {'fields': ('full_name', 'phone', 'role', 'telegram_id', 'telegram_username', 'created_at')}),
    )
    readonly_fields = ('created_at',)
    list_per_page = 30

    @admin.display(description='Role', ordering='role')
    def role_badge(self, obj):
        colors = {
            'ADMIN': '#2563eb',
            'DIRECTOR': '#059669',
            'MANAGER': '#d97706',
            'OBSERVER': '#64748b',
        }
        return format_html(
            '<span style="background:{};color:white;border-radius:999px;padding:4px 10px;font-weight:700;">{}</span>',
            colors.get(obj.role, '#64748b'),
            obj.get_role_display(),
        )

    @admin.display(description='Holat', boolean=True, ordering='is_active')
    def active_badge(self, obj):
        return obj.is_active


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'masked_token', 'expires_at', 'used_badge', 'used_at', 'created_at')
    list_filter = ('is_used', 'expires_at')
    search_fields = ('user__username', 'user__full_name', 'token')
    readonly_fields = ('created_at', 'updated_at', 'used_at', 'masked_token')
    fields = ('user', 'masked_token', 'expires_at', 'is_used', 'used_at', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_per_page = 30

    @admin.display(description='Token')
    def masked_token(self, obj):
        if not obj.token:
            return '-'
        return format_html('<code>{}...{}</code>', obj.token[:8], obj.token[-6:])

    @admin.display(description='Ishlatilgan', boolean=True, ordering='is_used')
    def used_badge(self, obj):
        return obj.is_used


@admin.register(TelegramLoginSession)
class TelegramLoginSessionAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'chat_id', 'telegram_username', 'phone', 'user', 'state_badge', 'last_interaction_at')
    list_filter = ('state', 'last_interaction_at')
    search_fields = ('telegram_id', 'telegram_username', 'phone', 'user__username', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at', 'last_interaction_at')
    date_hierarchy = 'last_interaction_at'
    list_per_page = 30

    @admin.display(description='Holat', ordering='state')
    def state_badge(self, obj):
        color = '#059669' if obj.state in {'LINKED', 'ACCESS_SENT'} else '#d97706'
        if obj.state in {'BLOCKED', 'ERROR'}:
            color = '#dc2626'
        return format_html(
            '<span style="background:{};color:white;border-radius:999px;padding:4px 10px;font-weight:700;">{}</span>',
            color,
            obj.get_state_display(),
        )


@admin.register(TelegramBotState)
class TelegramBotStateAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_update_id', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
