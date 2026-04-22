from django.views.generic import TemplateView

from apps.core.mixins import PageMetadataMixin, RoleRequiredMixin

from .forms import ReportFilterForm
from .selectors import category_report, report_totals, report_transactions, worker_payment_report
from .services import ReportExportService


class ReportsDashboardView(PageMetadataMixin, RoleRequiredMixin, TemplateView):
    template_name = 'reports/index.html'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'OBSERVER')
    page_title = 'Hisobotlar'
    page_subtitle = 'Transaction, obyekt, worker va kategoriya kesimlari'

    def get(self, request, *args, **kwargs):
        self.filter_form = ReportFilterForm(request.GET or None)
        filters = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        transactions = report_transactions(filters)
        if request.GET.get('export') == 'excel':
            return ReportExportService.export_transactions_excel(transactions)
        self.transactions = transactions[:30]
        self.worker_payments = worker_payment_report(filters)[:20]
        self.category_rows = category_report(filters)
        self.totals = report_totals(transactions)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = getattr(self, 'filter_form', ReportFilterForm())
        context['transactions'] = getattr(self, 'transactions', [])
        context['worker_payments'] = getattr(self, 'worker_payments', [])
        context['category_rows'] = getattr(self, 'category_rows', [])
        context['totals'] = getattr(self, 'totals', [])
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Hisobotlar', 'url': ''},
        ]
        return context
