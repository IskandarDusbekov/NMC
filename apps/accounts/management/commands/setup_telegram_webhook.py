"""
Telegram botni webhook rejimiga o'tkazish.

Ishlatish:
    python manage.py setup_telegram_webhook --url https://nurafshonmega.uz
    python manage.py setup_telegram_webhook --delete   # webhookni o'chirish (polling uchun)
    python manage.py setup_telegram_webhook --info      # hozirgi webhook holatini ko'rish
"""
from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.telegram_bot import TelegramBotApiClient, TelegramBotConfigService, TelegramBotFlowService


class Command(BaseCommand):
    help = 'Telegram botni webhook rejimiga o`tkazadi.'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, default='', help='Sayt domeningiz, masalan: https://nurafshonmega.uz')
        parser.add_argument('--secret', type=str, default='', help='Webhook secret (bo`sh qoldirilsa avtomatik yaratiladi)')
        parser.add_argument('--delete', action='store_true', help='Webhookni o`chirish (polling rejimiga qaytish)')
        parser.add_argument('--info', action='store_true', help='Hozirgi webhook holatini ko`rish')

    def handle(self, *args, **options):
        client = TelegramBotApiClient()

        # ── Webhook holati ko'rish ──────────────────────────────────────────
        if options['info']:
            try:
                info = client._request('getWebhookInfo')
                url = info.get('url') or '(bo`sh)'
                pending = info.get('pending_update_count', 0)
                last_err = info.get('last_error_message') or 'yo`q'
                last_err_date = info.get('last_error_date') or '-'
                self.stdout.write(self.style.SUCCESS(f'Webhook URL: {url}'))
                self.stdout.write(f'  Kutayotgan yangilanishlar : {pending}')
                self.stdout.write(f'  Oxirgi xato              : {last_err}')
                self.stdout.write(f'  Xato vaqti               : {last_err_date}')
            except Exception as exc:
                raise CommandError(f'Telegram API xatosi: {exc}') from exc
            return

        # ── Webhookni o'chirish ─────────────────────────────────────────────
        if options['delete']:
            try:
                client._request('deleteWebhook', {'drop_pending_updates': False})
                self.stdout.write(self.style.WARNING('Webhook o`chirildi. Bot endi polling rejimida ishlaydi.'))
                self.stdout.write('Polling uchun: python manage.py run_telegram_bot')
            except Exception as exc:
                raise CommandError(f'Webhook o`chirishda xato: {exc}') from exc
            return

        # ── Webhook o'rnatish ───────────────────────────────────────────────
        base_url = (options['url'] or TelegramBotConfigService.base_url()).rstrip('/')
        if not base_url.startswith('https://'):
            raise CommandError(
                'Telegram webhook faqat HTTPS URL qabul qiladi.\n'
                'Masalan: python manage.py setup_telegram_webhook --url https://nurafshonmega.uz'
            )

        webhook_url = f'{base_url}/accounts/telegram/webhook/'
        secret = options['secret'] or secrets.token_urlsafe(32)

        self.stdout.write(f'Webhook URL: {webhook_url}')
        self.stdout.write(f'Secret     : {secret}')
        self.stdout.write('')

        try:
            client._request('setWebhook', {
                'url': webhook_url,
                'secret_token': secret,
                'allowed_updates': ['message'],
                'drop_pending_updates': False,
            })
            TelegramBotFlowService.sync_commands(client)
        except Exception as exc:
            raise CommandError(f'Webhook o`rnatishda xato: {exc}') from exc

        self.stdout.write(self.style.SUCCESS('✅ Webhook muvaffaqiyatli o`rnatildi!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('━━━ Serverdagi .env ga quyidagilarni qo`shing ━━━'))
        self.stdout.write(f'APP_BASE_URL={base_url}')
        self.stdout.write(f'TELEGRAM_WEBHOOK_SECRET={secret}')
        self.stdout.write(self.style.WARNING('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'))
        self.stdout.write('')
        self.stdout.write('Shundan keyin:  touch tmp/restart.txt')
        self.stdout.write('Polling jarayonini to`xtating (agar ishlayotgan bo`lsa):')
        self.stdout.write('  pkill -f run_telegram_bot')
