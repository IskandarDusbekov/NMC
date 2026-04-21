from django.urls import path

from .views import (
    CategoryManagementView,
    ExchangeRateManagementView,
    ManagerAccountListView,
    ManagerExpenseCreateView,
    ManagerReturnCreateView,
    ManagerTransferCreateView,
    TransactionCreateView,
    TransactionDeleteView,
    TransactionListView,
    TransactionUpdateView,
)

app_name = 'finance'

urlpatterns = [
    path('finance/transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('finance/transactions/create/', TransactionCreateView.as_view(), name='transaction-create'),
    path('finance/transactions/<int:pk>/edit/', TransactionUpdateView.as_view(), name='transaction-update'),
    path('finance/transactions/<int:pk>/delete/', TransactionDeleteView.as_view(), name='transaction-delete'),
    path('finance/manager-accounts/', ManagerAccountListView.as_view(), name='manager-account-list'),
    path('finance/transfers/create/', ManagerTransferCreateView.as_view(), name='manager-transfer-create'),
    path('finance/manager-returns/create/', ManagerReturnCreateView.as_view(), name='manager-return-create'),
    path('finance/manager-expenses/create/', ManagerExpenseCreateView.as_view(), name='manager-expense-create'),
    path('finance/categories/', CategoryManagementView.as_view(), name='category-list'),
    path('finance/exchange-rates/', ExchangeRateManagementView.as_view(), name='exchange-rate-list'),
]
