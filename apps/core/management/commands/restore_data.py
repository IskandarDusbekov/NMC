from pathlib import Path

from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    help = 'JSON backup fayldan ma`lumotlarni tiklaydi.'

    def add_arguments(self, parser):
        parser.add_argument('backup_file', help='Tiklanadigan JSON backup fayl yo`li.')

    def handle(self, *args, **options):
        backup_file = Path(options['backup_file'])
        if not backup_file.exists():
            raise CommandError(f'Backup fayl topilmadi: {backup_file}')
        call_command('loaddata', str(backup_file))
        self.stdout.write(self.style.SUCCESS(f'Ma`lumotlar tiklandi: {backup_file}'))
