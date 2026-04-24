from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import Http404
from django.shortcuts import redirect
from django.urls import include, path

from apps.core.admin_views import download_json_backup

admin.site.site_header = getattr(settings, 'ADMIN_SITE_HEADER', 'NurafshonMega Ferma admin panel')
admin.site.site_title = getattr(settings, 'ADMIN_SITE_TITLE', 'Ferma admin')
admin.site.index_title = getattr(settings, 'ADMIN_INDEX_TITLE', 'Sozlamalar va ma`lumotlar boshqaruvi')


def hidden_admin_disabled(_request, *_args, **_kwargs):
    raise Http404


admin_url = getattr(settings, 'ADMIN_URL_PATH', 'secure-console/')

urlpatterns = [
    path('', lambda request: redirect('dashboard:index')),
    path(f'{admin_url}backup-json/', admin.site.admin_view(download_json_backup), name='admin-backup-json'),
    path(admin_url, admin.site.urls),
    path('admin/', hidden_admin_disabled),
    path('admin/<path:_extra>/', hidden_admin_disabled),
    path('accounts/', include(('apps.accounts.urls', 'accounts'), namespace='accounts')),
    path('', include(('apps.dashboard.urls', 'dashboard'), namespace='dashboard')),
    path('', include(('apps.objects.urls', 'objects'), namespace='objects')),
    path('', include(('apps.finance.urls', 'finance'), namespace='finance')),
    path('', include(('apps.workforce.urls', 'workforce'), namespace='workforce')),
    path('', include(('apps.reports.urls', 'reports'), namespace='reports')),
    path('', include(('apps.logs.urls', 'logs'), namespace='logs')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
