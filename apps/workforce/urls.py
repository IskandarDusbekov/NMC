from django.urls import path

from .views import (
    SalaryPaymentCreateView,
    SalaryPaymentListView,
    SalaryPaymentReceiptView,
    WorkerCreateView,
    WorkerDeleteView,
    WorkerDetailView,
    WorkerListView,
    WorkerUpdateView,
)

app_name = 'workforce'

urlpatterns = [
    path('workers/', WorkerListView.as_view(), name='worker-list'),
    path('workers/create/', WorkerCreateView.as_view(), name='worker-create'),
    path('workers/<int:pk>/', WorkerDetailView.as_view(), name='worker-detail'),
    path('workers/<int:pk>/edit/', WorkerUpdateView.as_view(), name='worker-update'),
    path('workers/<int:pk>/delete/', WorkerDeleteView.as_view(), name='worker-delete'),
    path('salary-payments/', SalaryPaymentListView.as_view(), name='salary-payment-list'),
    path('salary-payments/create/', SalaryPaymentCreateView.as_view(), name='salary-payment-create'),
    path('salary-payments/<int:pk>/receipt/', SalaryPaymentReceiptView.as_view(), name='salary-payment-receipt'),
]
