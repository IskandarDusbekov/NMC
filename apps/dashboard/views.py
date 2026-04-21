from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.generic import TemplateView

from apps.core.mixins import PageMetadataMixin, RoleRequiredMixin

from .services import DashboardService


class DashboardView(PageMetadataMixin, RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Dashboard'
    page_subtitle = 'Global balans, obyektlar va pul oqimining markaziy ko`rinishi'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        overview = DashboardService.overview(timezone.now().date(), self.request.user)
        context.update(overview)
        context['today_expense_total'] = overview['today_expense'].aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        context['today_income_total'] = overview['today_income'].aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        context['today_company_expense_total'] = overview['today_company_expense'].aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        context['today_manager_expense_total'] = overview['today_manager_expense'].aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        context['breadcrumbs'] = [{'label': 'Dashboard', 'url': ''}]
        return context
