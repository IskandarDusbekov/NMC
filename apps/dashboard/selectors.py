from apps.finance.selectors import category_summary, daily_expense_series, monthly_expense_series, recent_transactions
from apps.workforce.selectors import recent_salary_payments


def dashboard_recent_transactions(user=None):
    return recent_transactions(user=user)


def dashboard_salary_payments(user=None):
    return recent_salary_payments(user=user)


def dashboard_charts(user=None):
    return {
        'category_distribution': category_summary(user=user),
        'daily_expense_series': daily_expense_series(user=user),
        'monthly_expense_series': monthly_expense_series(user=user),
    }
