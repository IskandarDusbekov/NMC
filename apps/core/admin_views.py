from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.logs.services import AuditLogService


# ────────── helpers ──────────
def _require_superuser(request):
    if not getattr(request.user, 'is_superuser', False):
        AuditLogService.log_from_request(
            request,
            user=getattr(request, 'user', None),
            action='security_backup_denied',
            model_name='Backup',
            object_id='json',
            description='Backup sahifasiga ruxsatsiz kirish urinishi.',
        )
        raise PermissionDenied


def _backup_dir() -> Path:
    d = Path(getattr(settings, 'BACKUP_DIR', 'backups'))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _existing_backups() -> list[dict]:
    backups = []
    for f in sorted(_backup_dir().glob('*.json'), reverse=True):
        stat = f.stat()
        backups.append({
            'name': f.name,
            'size_kb': round(stat.st_size / 1024, 1),
            'modified': timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone()),
        })
    return backups


# ────────── views ──────────
def backup_dashboard(request):
    """Admin backup boshqaruv sahifasi."""
    _require_superuser(request)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ---------- DOWNLOAD NEW ----------
        if action == 'create_backup':
            ts = timezone.now().strftime('%Y%m%d-%H%M%S')
            filename = _backup_dir() / f'nmc-backup-{ts}.json'
            with filename.open('w', encoding='utf-8') as out:
                call_command(
                    'dumpdata',
                    '--natural-foreign', '--natural-primary',
                    '--exclude=contenttypes', '--exclude=auth.permission',
                    stdout=out,
                )
            AuditLogService.log_from_request(
                request, user=request.user,
                action='backup_created', model_name='Backup',
                object_id=filename.name,
                description=f'Yangi JSON backup yaratildi: {filename.name}',
            )
            messages.success(request, f'✅ Backup yaratildi: {filename.name}')
            return redirect(request.path)

        # ---------- DOWNLOAD FILE ----------
        if action == 'download':
            fname = request.POST.get('filename', '')
            fpath = _backup_dir() / fname
            if not fpath.exists() or '..' in fname or not fname.endswith('.json'):
                messages.error(request, 'Fayl topilmadi.')
                return redirect(request.path)
            content = fpath.read_bytes()
            response = HttpResponse(content, content_type='application/json; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{fname}"'
            return response

        # ---------- DELETE FILE ----------
        if action == 'delete_backup':
            fname = request.POST.get('filename', '')
            fpath = _backup_dir() / fname
            if fpath.exists() and '..' not in fname and fname.endswith('.json'):
                fpath.unlink()
                AuditLogService.log_from_request(
                    request, user=request.user,
                    action='backup_deleted', model_name='Backup',
                    object_id=fname, description=f'Backup o`chirildi: {fname}',
                )
                messages.success(request, f'🗑 Backup o`chirildi: {fname}')
            else:
                messages.error(request, 'Fayl topilmadi yoki ruxsat yo`q.')
            return redirect(request.path)

        # ---------- UPLOAD & RESTORE ----------
        if action == 'restore':
            uploaded = request.FILES.get('backup_file')
            if not uploaded or not uploaded.name.endswith('.json'):
                messages.error(request, '❌ Faqat .json formatdagi fayl yuklab berish mumkin.')
                return redirect(request.path)
            try:
                raw = uploaded.read().decode('utf-8')
                json.loads(raw)  # validate JSON
            except (UnicodeDecodeError, json.JSONDecodeError):
                messages.error(request, '❌ Fayl noto`g`ri JSON format.')
                return redirect(request.path)

            # save uploaded file to backups dir
            ts = timezone.now().strftime('%Y%m%d-%H%M%S')
            saved_path = _backup_dir() / f'nmc-restore-{ts}.json'
            saved_path.write_text(raw, encoding='utf-8')

            try:
                call_command('loaddata', str(saved_path), verbosity=0)
            except Exception as exc:
                messages.error(request, f'❌ Tiklashda xatolik: {exc}')
                AuditLogService.log_from_request(
                    request, user=request.user,
                    action='backup_restore_failed', model_name='Backup',
                    object_id=saved_path.name,
                    description=f'Backup tiklash xato: {exc}',
                )
                return redirect(request.path)

            AuditLogService.log_from_request(
                request, user=request.user,
                action='backup_restored', model_name='Backup',
                object_id=saved_path.name,
                description=f'Ma`lumotlar JSON backupdan tiklandi: {saved_path.name}',
            )
            messages.success(request, f'✅ Ma`lumotlar muvaffaqiyatli tiklandi: {saved_path.name}')
            return redirect(request.path)

    context = {
        'title': 'Backup boshqaruvi',
        'backups': _existing_backups(),
        'opts': {'app_label': 'core'},
        'has_permission': True,
    }
    return render(request, 'admin/backup_dashboard.html', context)


# ────────── legacy download-only view (kept for URL compatibility) ──────────
def download_json_backup(request):
    """Tezkor backup yuklab olish (superuser only)."""
    _require_superuser(request)
    buffer = StringIO()
    call_command(
        'dumpdata',
        '--natural-foreign', '--natural-primary',
        '--exclude=contenttypes', '--exclude=auth.permission',
        stdout=buffer,
    )
    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    AuditLogService.log_from_request(
        request, user=request.user,
        action='backup_json_downloaded', model_name='Backup',
        object_id=timestamp, description='JSON backup yuklab olindi (tezkor).',
    )
    response = HttpResponse(buffer.getvalue(), content_type='application/json; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="nmc-backup-{timestamp}.json"'
    return response
