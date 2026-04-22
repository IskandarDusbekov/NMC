from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.forms import ConfirmDeleteForm
from apps.core.mixins import PageMetadataMixin, RoleRequiredMixin
from apps.finance.views import _apply_validation_error
from apps.logs.services import AuditLogService

from .forms import SalaryPaymentForm, WorkerForm
from .models import Worker
from .selectors import recent_salary_payments, worker_queryset
from .services import SalaryPaymentService


class WorkerListView(PageMetadataMixin, RoleRequiredMixin, ListView):
    template_name = 'workforce/worker_list.html'
    context_object_name = 'workers'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER')
    page_title = 'Ishchilar'
    page_subtitle = 'Oylik va brigade xodimlari bo`yicha hisob'

    def get_queryset(self):
        return worker_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Ishchilar', 'url': ''},
        ]
        return context


class WorkerDetailView(PageMetadataMixin, RoleRequiredMixin, DetailView):
    template_name = 'workforce/worker_detail.html'
    context_object_name = 'worker'
    queryset = worker_queryset()
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER')
    page_title = 'Worker detali'
    page_subtitle = 'To`lovlar, obyekt birikmalari va umumiy xarajatlar'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['salary_payments'] = self.object.salary_payments.select_related('object')[:20]
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Ishchilar', 'url': reverse('workforce:worker-list')},
            {'label': self.object.full_name, 'url': ''},
        ]
        return context


class WorkerCreateView(PageMetadataMixin, RoleRequiredMixin, CreateView):
    template_name = 'workforce/worker_form.html'
    form_class = WorkerForm
    success_url = reverse_lazy('workforce:worker-list')
    allowed_roles = ('ADMIN', 'DIRECTOR')
    page_title = 'Yangi worker'
    page_subtitle = 'Faqat kerakli maydonlar bilan yangi worker yarating'

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLogService.log_from_request(
            self.request,
            action='worker_created',
            model_name='Worker',
            object_id=str(self.object.pk),
            description=f'{self.object.full_name} worker yaratildi.',
        )
        messages.success(self.request, 'Worker yaratildi.')
        return response


class WorkerUpdateView(PageMetadataMixin, RoleRequiredMixin, UpdateView):
    template_name = 'workforce/worker_form.html'
    form_class = WorkerForm
    queryset = Worker.objects.all()
    success_url = reverse_lazy('workforce:worker-list')
    allowed_roles = ('ADMIN', 'DIRECTOR')
    page_title = 'Workerni tahrirlash'
    page_subtitle = 'Worker turi va asosiy ma`lumotlarini yangilang'

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLogService.log_from_request(
            self.request,
            action='worker_updated',
            model_name='Worker',
            object_id=str(self.object.pk),
            description=f'{self.object.full_name} worker yangilandi.',
        )
        messages.success(self.request, 'Worker yangilandi.')
        return response


class WorkerDeleteView(PageMetadataMixin, RoleRequiredMixin, View):
    template_name = 'confirm_delete.html'
    allowed_roles = ('ADMIN',)
    page_title = 'Workerni ochirish'
    page_subtitle = 'Xavfsiz ochirish uchun alohida tasdiqlash'

    def get(self, request, pk):
        instance = get_object_or_404(Worker, pk=pk)
        return render(
            request,
            self.template_name,
            {
                'form': ConfirmDeleteForm(),
                'object_label': instance.full_name,
                'cancel_url': reverse_lazy('workforce:worker-list'),
                'page_title': self.page_title,
                'page_subtitle': self.page_subtitle,
            },
        )

    def post(self, request, pk):
        instance = get_object_or_404(Worker, pk=pk)
        form = ConfirmDeleteForm(request.POST)
        if form.is_valid():
            full_name = instance.full_name
            instance.delete()
            AuditLogService.log_from_request(
                request,
                action='worker_deleted',
                model_name='Worker',
                object_id=str(pk),
                description=f'{full_name} worker ochirildi.',
            )
            messages.success(request, 'Worker ochirildi.')
            return redirect('workforce:worker-list')
        return render(request, self.template_name, {'form': form, 'object_label': instance.full_name, 'cancel_url': reverse_lazy('workforce:worker-list')})


class SalaryPaymentListView(PageMetadataMixin, RoleRequiredMixin, ListView):
    template_name = 'workforce/salary_payment_list.html'
    context_object_name = 'salary_payments'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER')
    page_title = 'Salary paymentlar'
    page_subtitle = 'Ishchilarga berilgan to`lovlar va obyekt bog`lanishi'

    def get_queryset(self):
        return recent_salary_payments(limit=50, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payments = list(self.object_list)
        context['total_salary_uzs'] = sum((item.amount for item in payments if item.currency == 'UZS'), Decimal('0.00'))
        context['total_salary_usd'] = sum((item.amount for item in payments if item.currency == 'USD'), Decimal('0.00'))
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Salary paymentlar', 'url': ''},
        ]
        return context


class SalaryPaymentCreateView(PageMetadataMixin, RoleRequiredMixin, View):
    template_name = 'workforce/salary_payment_form.html'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Salary payment yaratish'
    page_subtitle = 'To`lov yaratilganda avtomatik transaction ham ochiladi'

    def _build_context(self, form):
        return {
            'form': form,
            'page_title': self.page_title,
            'page_subtitle': self.page_subtitle,
            'breadcrumbs': [
                {'label': 'Dashboard', 'url': '/dashboard/'},
                {'label': 'Salary paymentlar', 'url': reverse('workforce:salary-payment-list')},
                {'label': 'Yaratish', 'url': ''},
            ],
        }

    def get(self, request):
        return render(request, self.template_name, self._build_context(SalaryPaymentForm(user=request.user)))

    def post(self, request):
        form = SalaryPaymentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                SalaryPaymentService.create_salary_payment(user=request.user, request=request, **form.cleaned_data)
            except ValidationError as error:
                _apply_validation_error(form, error)
                return render(request, self.template_name, self._build_context(form))
            messages.success(request, 'Salary payment yaratildi.')
            return redirect('workforce:salary-payment-list')
        return render(request, self.template_name, self._build_context(form))
