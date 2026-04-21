from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AccessToken, TelegramBotState, TelegramLoginSession, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'full_name', 'role', 'phone', 'telegram_id', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'full_name', 'phone', 'telegram_username', 'telegram_id')
    ordering = ('username',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional info', {'fields': ('full_name', 'phone', 'role', 'telegram_id', 'telegram_username', 'created_at')}),
    )
    readonly_fields = ('created_at',)


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'is_used', 'used_at', 'created_at')
    list_filter = ('is_used', 'expires_at')
    search_fields = ('user__username', 'user__full_name', 'token')
    readonly_fields = ('created_at', 'updated_at', 'used_at')


@admin.register(TelegramLoginSession)
class TelegramLoginSessionAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'chat_id', 'telegram_username', 'phone', 'user', 'state', 'last_interaction_at')
    list_filter = ('state', 'last_interaction_at')
    search_fields = ('telegram_id', 'telegram_username', 'phone', 'user__username', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at', 'last_interaction_at')


@admin.register(TelegramBotState)
class TelegramBotStateAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_update_id', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
