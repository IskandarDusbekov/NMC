from django.urls import path

from .views import AuditLogListView

app_name = 'logs'

urlpatterns = [
    path('logs/', AuditLogListView.as_view(), name='index'),
]
