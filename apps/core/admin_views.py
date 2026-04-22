from io import StringIO

from django.core.management import call_command
from django.http import HttpResponse
from django.utils import timezone


def download_json_backup(request):
    buffer = StringIO()
    call_command(
        'dumpdata',
        '--natural-foreign',
        '--natural-primary',
        '--exclude=contenttypes',
        '--exclude=auth.permission',
        stdout=buffer,
    )
    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    response = HttpResponse(buffer.getvalue(), content_type='application/json; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="nmc-backup-{timestamp}.json"'
    return response
