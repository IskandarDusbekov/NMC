from __future__ import annotations

import time

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from apps.accounts.telegram_bot import TelegramBotApiClient, TelegramBotFlowService, TelegramBotStateService


class Command(BaseCommand):
    help = 'Telegram botni polling rejimida ishga tushiradi.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Faqat bitta polling siklini bajaradi.')
        parser.add_argument('--timeout', type=int, default=20, help='Telegram getUpdates timeout qiymati.')
        parser.add_argument('--pause', type=float, default=1.5, help='Bo`sh pollingdan keyingi kutish vaqti.')
        parser.add_argument('--state-name', default='default', help='Offset saqlanadigan bot state nomi.')

    def handle(self, *args, **options):
        client = TelegramBotApiClient()
        try:
            TelegramBotFlowService.sync_commands(client)
        except ValidationError as error:
            self.stderr.write(self.style.WARNING(f'Telegram commands sync xatosi: {error}'))

        once = options['once']
        timeout = options['timeout']
        pause = options['pause']
        state_name = options['state_name']

        self.stdout.write(self.style.SUCCESS('Telegram bot polling boshlandi.'))

        while True:
            try:
                offset = TelegramBotStateService.current_offset(name=state_name)
                updates = client.get_updates(offset=offset or None, timeout=timeout)
            except ValidationError as error:
                self.stderr.write(self.style.WARNING(f'Telegram polling xatosi: {error}'))
                if once:
                    break
                time.sleep(max(pause, 5))
                continue

            if not updates:
                if once:
                    break
                time.sleep(pause)
                continue

            for update in updates:
                update_id = update.get('update_id', 0)
                try:
                    TelegramBotFlowService.process_update(update, client=client)
                except ValidationError as error:
                    self.stderr.write(self.style.WARNING(f'Telegram update #{update_id} xatosi: {error}'))
                except Exception as error:  # noqa: BLE001
                    self.stderr.write(self.style.ERROR(f'Telegram update #{update_id} kutilmagan xato: {error}'))
                finally:
                    TelegramBotStateService.store_offset(update_id + 1, name=state_name)

            if once:
                break
