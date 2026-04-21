from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import include, path

urlpatterns = [
    path('', lambda request: redirect('dashboard:index')),
    path('admin/', admin.site.urls),
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
