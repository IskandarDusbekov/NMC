from django.views.generic import ListView

from apps.core.mixins import PageMetadataMixin, RoleRequiredMixin

from .forms import AuditLogFilterForm
from .selectors import audit_log_list


class AuditLogListView(PageMetadataMixin, RoleRequiredMixin, ListView):
    template_name = 'logs/index.html'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'OBSERVER')
    context_object_name = 'logs'
    paginate_by = 20
    page_title = 'Audit loglar'
    page_subtitle = 'Tizimdagi muhim amallar tarixi'

    def get_queryset(self):
        self.filter_form = AuditLogFilterForm(self.request.GET or None)
        if self.filter_form.is_valid():
            return audit_log_list(self.filter_form.cleaned_data)
        return audit_log_list()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Loglar', 'url': ''},
        ]
        return context
