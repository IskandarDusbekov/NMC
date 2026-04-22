from django.core.exceptions import ValidationError
from django.core.management import BaseCommand, CommandError

from apps.finance.services import ExchangeRateService


class Command(BaseCommand):
    help = 'CBU API orqali USD kursini yangilaydi.'

    def add_arguments(self, parser):
        parser.add_argument('--quiet', action='store_true', help='Muvaffaqiyatli natijani terminalga chiqarmaydi.')

    def handle(self, *args, **options):
        try:
            rate = ExchangeRateService.update_rate_from_cbu(user=None)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages if hasattr(exc, 'messages') else [str(exc)])) from exc

        if not options['quiet']:
            self.stdout.write(self.style.SUCCESS(f'USD kurs yangilandi: {rate.usd_to_uzs} UZS'))
