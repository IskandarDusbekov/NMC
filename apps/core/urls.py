from django.urls import path

from .views import (
    FileDeleteView,
    FileDownloadView,
    FileListView,
    FileUploadView,
    home_redirect,
)

app_name = 'core'

urlpatterns = [
    path('', home_redirect, name='home'),
    # ── Fayl arxivi ──────────────────────────────────────────────────────────
    path('files/',                       FileListView.as_view(),     name='file-list'),
    path('files/upload/',                FileUploadView.as_view(),   name='file-upload'),
    path('files/<uuid:uid>/download/',   FileDownloadView.as_view(), name='file-download'),
    path('files/<uuid:uid>/delete/',     FileDeleteView.as_view(),   name='file-delete'),
]
