from django.urls import path

from .views import ReportsDashboardView

app_name = 'reports'

urlpatterns = [
    path('reports/', ReportsDashboardView.as_view(), name='index'),
]
