from .models import AuditLog


def audit_log_list(filters=None):
    queryset = AuditLog.objects.select_related('user')
    filters = filters or {}
    if filters.get('action'):
        queryset = queryset.filter(action__icontains=filters['action'])
    if filters.get('model_name'):
        queryset = queryset.filter(model_name__icontains=filters['model_name'])
    return queryset
