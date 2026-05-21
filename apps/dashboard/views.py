import json
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.generic import TemplateView

from apps.core.mixins import PageMetadataMixin, RoleRequiredMixin

from .services import DashboardService


class DashboardView(PageMetadataMixin, RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER')
    page_title = 'Dashboard'
    page_subtitle = 'Global balans, obyektlar va pul oqimining markaziy ko`rinishi'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        overview = DashboardService.overview(timezone.now().date(), self.request.user)
        context.update(overview)

        # ── Bugungi jami ────────────────────────────────────────────────────
        ZERO = Decimal('0.00')
        context['today_expense_total']         = overview['today_expense'].aggregate(        t=Coalesce(Sum('amount'), ZERO))['t']
        context['today_income_total']          = overview['today_income'].aggregate(         t=Coalesce(Sum('amount'), ZERO))['t']
        context['today_company_expense_total'] = overview['today_company_expense'].aggregate(t=Coalesce(Sum('amount'), ZERO))['t']
        context['today_manager_expense_total'] = overview['today_manager_expense'].aggregate(t=Coalesce(Sum('amount'), ZERO))['t']

        # ── Chart.js JSON ma'lumotlari ───────────────────────────────────────
        monthly = overview['monthly_expense_series']
        context['chart_monthly_labels'] = json.dumps([r['label'] for r in monthly], ensure_ascii=False)
        context['chart_monthly_uzs']    = json.dumps([float(r['UZS']) for r in monthly])
        context['chart_monthly_usd']    = json.dumps([float(r['USD']) for r in monthly])

        daily = overview['daily_expense_series']
        context['chart_daily_labels'] = json.dumps([r['label'] for r in daily], ensure_ascii=False)
        context['chart_daily_uzs']    = json.dumps([float(r['UZS']) for r in daily])

        cat = overview['category_distribution']
        context['chart_cat_labels'] = json.dumps([r['label'] for r in cat], ensure_ascii=False)
        context['chart_cat_values'] = json.dumps([float(r['total']) for r in cat])
        context['chart_cat_colors'] = json.dumps([r['color'] for r in cat])

        context['breadcrumbs'] = [{'label': 'Dashboard', 'url': ''}]
        return context
