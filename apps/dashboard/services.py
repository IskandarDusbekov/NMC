from apps.finance.models import TransactionTypeChoices, WalletTypeChoices
from apps.finance.selectors import recent_transfers, top_manager_spending, transaction_list
from apps.finance.services import CompanyBalanceService, ManagerBalanceService
from apps.objects.models import ConstructionObject
from apps.objects.services import ObjectAnalyticsService
from apps.workforce.models import Worker

from .selectors import dashboard_charts, dashboard_recent_transactions, dashboard_salary_payments


class DashboardService:
    @staticmethod
    def overview(today, user):
        today_transactions = transaction_list({'date_from': today, 'date_to': today}, user=user)
        is_manager = getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False)
        if is_manager and hasattr(user, 'manager_account'):
            balances = ManagerBalanceService.summary_for_account(user.manager_account)
        else:
            balances = CompanyBalanceService.summary()
        return {
            'balances': balances,
            'today_expense': today_transactions.filter(type=TransactionTypeChoices.EXPENSE),
            'today_income': today_transactions.filter(type=TransactionTypeChoices.INCOME),
            'today_company_expense': today_transactions.filter(type=TransactionTypeChoices.EXPENSE, wallet_type=WalletTypeChoices.COMPANY),
            'today_manager_expense': today_transactions.filter(type=TransactionTypeChoices.EXPENSE, wallet_type=WalletTypeChoices.MANAGER),
            'active_objects': ConstructionObject.objects.filter(status=ConstructionObject.Status.ACTIVE).count(),
            'worker_count': Worker.objects.filter(is_active=True).count(),
            'recent_transactions': dashboard_recent_transactions(user=user),
            'top_objects': ObjectAnalyticsService.top_expense_objects(),
            'progress_objects': ObjectAnalyticsService.progress_objects(),
            'recent_salary_payments': dashboard_salary_payments(user=user),
            'recent_transfers': recent_transfers(user=user),
            'top_manager_spending': top_manager_spending(),
            'manager_holdings': ManagerBalanceService.total_manager_holdings(),
            'is_manager_dashboard': is_manager,
            **dashboard_charts(user=user),
        }
