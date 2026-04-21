from pathlib import Path

from django.core.management import BaseCommand, call_command
from django.utils import timezone


class Command(BaseCommand):
    help = 'Loyiha ma`lumotlarini JSON backup qilib saqlaydi.'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', default='backups', help='Backup saqlanadigan papka.')

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = output_dir / f'nmc-backup-{timezone.now().strftime("%Y%m%d-%H%M%S")}.json'
        with filename.open('w', encoding='utf-8') as output:
            call_command(
                'dumpdata',
                '--natural-foreign',
                '--natural-primary',
                '--exclude=contenttypes',
                '--exclude=auth.permission',
                stdout=output,
            )
        self.stdout.write(self.style.SUCCESS(f'Backup tayyor: {filename}'))
