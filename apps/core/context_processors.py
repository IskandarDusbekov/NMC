from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.utils import OperationalError, ProgrammingError

from apps.core.services import NavigationService


def global_layout(request):
    try:
        from apps.finance.services import CompanyBalanceService, ExchangeRateService, ManagerBalanceService, TransferService

        company_balances = CompanyBalanceService.summary()
        manager_holdings = ManagerBalanceService.total_manager_holdings()
        today_transfer_count = TransferService.today_transfer_count()
        if getattr(request.user, 'is_authenticated', False) and getattr(request.user, 'role', '') == 'MANAGER' and hasattr(request.user, 'manager_account'):
            balances = ManagerBalanceService.summary_for_account(request.user.manager_account)
        else:
            balances = company_balances
        exchange_rate = ExchangeRateService.latest_rate(
            auto_update=True,
            user=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )
    except (OperationalError, ProgrammingError, ImportError, ValidationError):
        balances = {'UZS': 0, 'USD': 0}
        company_balances = {'UZS': 0, 'USD': 0}
        manager_holdings = {'UZS': 0, 'USD': 0}
        today_transfer_count = 0
        exchange_rate = None

    navigation = NavigationService.build_navigation(request.user)
    return {
        'ui_balances': balances,
        'ui_company_balances': company_balances,
        'ui_manager_holdings': manager_holdings,
        'ui_today_transfer_count': today_transfer_count,
        'ui_exchange_rate': exchange_rate,
        'navigation_items': navigation,
        'mobile_navigation_items': [item for item in navigation if item['mobile']][:4],
    }
