from io import StringIO

from django.core.management import call_command
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone

from apps.logs.services import AuditLogService


def download_json_backup(request):
    if not getattr(request.user, 'is_superuser', False):
        AuditLogService.log_from_request(
            request,
            user=getattr(request, 'user', None),
            action='security_backup_download_denied',
            model_name='Backup',
            object_id='json',
            description='JSON backup yuklab olish urinishiga ruxsat berilmadi.',
        )
        raise PermissionDenied

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
    AuditLogService.log_from_request(
        request,
        user=request.user,
        action='backup_json_downloaded',
        model_name='Backup',
        object_id=timestamp,
        description='JSON backup yuklab olindi.',
    )
    response = HttpResponse(buffer.getvalue(), content_type='application/json; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="nmc-backup-{timestamp}.json"'
    return response
