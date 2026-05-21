import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# ── Fayl validatsiya ──────────────────────────────────────────────────────────
_ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.jpg', '.jpeg', '.png', '.webp',
    '.zip', '.rar', '.txt', '.csv',
}
_ALLOWED_MIME = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg', 'image/png', 'image/webp',
    'application/zip', 'application/x-rar-compressed',
    'application/x-zip-compressed', 'multipart/x-zip',
    'text/plain', 'text/csv',
}
_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
_EXT_ICON = {
    '.pdf': '📄', '.doc': '📝', '.docx': '📝',
    '.xls': '📊', '.xlsx': '📊', '.csv': '📊',
    '.jpg': '🖼', '.jpeg': '🖼', '.png': '🖼', '.webp': '🖼',
    '.zip': '🗜', '.rar': '🗜', '.txt': '📃',
}


def _validate_project_file(file):
    if not file:
        return file
    ext = Path(file.name).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'Ruxsat etilmagan fayl turi "{ext}". '
            f'Mumkin: {", ".join(sorted(_ALLOWED_EXTENSIONS))}'
        )
    if file.size > _MAX_FILE_SIZE:
        raise ValidationError(
            f'Fayl juda katta ({file.size // (1024*1024)} MB). '
            f'Maksimal: {_MAX_FILE_SIZE // (1024*1024)} MB.'
        )
    mime = getattr(file, 'content_type', '') or ''
    if mime and mime not in _ALLOWED_MIME:
        raise ValidationError(f'Ruxsat etilmagan MIME turi: {mime}')
    return file


def _file_upload_path(instance, filename):
    ext = Path(filename).suffix.lower()
    uid = uuid.uuid4().hex
    return f'project_files/{uid[:2]}/{uid}{ext}'


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='%(class)s_deleted_set',
    )

    class Meta:
        abstract = True


class ProjectFile(TimeStampedModel):
    """Loyiha fayllari — obyektga bog'liq yoki umumiy arxiv."""

    class Category(models.TextChoices):
        CONTRACT = 'contract', 'Shartnoma'
        ESTIMATE = 'estimate', 'Smeta'
        PERMIT   = 'permit',   'Ruxsatnoma'
        PHOTO    = 'photo',    'Foto'
        REPORT   = 'report',   'Hisobot'
        INVOICE  = 'invoice',  'Hisob-faktura'
        OTHER    = 'other',    'Boshqa'

    uid      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    object   = models.ForeignKey(
        'objects.ConstructionObject',
        blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='files',
        verbose_name='Obyekt',
    )
    title       = models.CharField(max_length=255, verbose_name='Sarlavha')
    description = models.TextField(blank=True, verbose_name='Izoh')
    category    = models.CharField(
        max_length=20, choices=Category.choices,
        default=Category.OTHER, verbose_name='Kategoriya',
    )
    file              = models.FileField(
        upload_to=_file_upload_path,
        validators=[_validate_project_file],
        verbose_name='Fayl',
    )
    original_filename = models.CharField(max_length=255, blank=True)
    file_size         = models.PositiveIntegerField(default=0)
    file_ext          = models.CharField(max_length=10, blank=True)
    uploaded_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_files',
        verbose_name='Yuklagan',
    )

    class Meta:
        verbose_name        = 'Loyiha fayli'
        verbose_name_plural = 'Loyiha fayllari'
        ordering            = ('-created_at',)
        indexes = [
            models.Index(fields=['object', '-created_at'],     name='pf_object_date_idx'),
            models.Index(fields=['category', '-created_at'],   name='pf_category_date_idx'),
            models.Index(fields=['uploaded_by', '-created_at'], name='pf_uploader_date_idx'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'name'):
            if not self.original_filename:
                self.original_filename = Path(self.file.name).name
            self.file_size = getattr(self.file, 'size', self.file_size) or self.file_size
            self.file_ext  = Path(self.file.name).suffix.lower()
        super().save(*args, **kwargs)

    @property
    def icon(self):
        return _EXT_ICON.get(self.file_ext, '📎')

    @property
    def size_display(self):
        if self.file_size < 1024:
            return f'{self.file_size} B'
        if self.file_size < 1024 * 1024:
            return f'{self.file_size / 1024:.1f} KB'
        return f'{self.file_size / (1024 * 1024):.1f} MB'
