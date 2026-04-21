from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.forms import ConfirmDeleteForm
from apps.core.mixins import DirectorRequiredMixin, PageMetadataMixin, RoleRequiredMixin
from apps.finance.models import TransactionCategory
from apps.logs.services import AuditLogService

from .forms import ConstructionObjectCreateForm, ConstructionObjectUpdateForm, ObjectExpenseForm, ObjectWorkItemPaymentForm, WorkItemForm
from .models import ConstructionObject, WorkItem
from .selectors import construction_object_queryset, work_item_queryset
from .services import ObjectAnalyticsService, ObjectFinanceService


def _apply_validation_error(form, error: ValidationError):
    if hasattr(error, 'message_dict'):
        for field, messages in error.message_dict.items():
            for message in messages:
                if field == '__all__':
                    form.add_error(None, message)
                else:
                    form.add_error(field, message)
        return
    for message in error.messages:
        form.add_error(None, message)


class ConstructionObjectListView(PageMetadataMixin, RoleRequiredMixin, ListView):
    template_name = 'objects/object_list.html'
    context_object_name = 'objects_list'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Qurilish obyektlari'
    page_subtitle = 'Real pul emas, analytics va progress boshqaruvi'

    def get_queryset(self):
        return construction_object_queryset()


class ConstructionObjectDetailView(PageMetadataMixin, RoleRequiredMixin, DetailView):
    template_name = 'objects/object_detail.html'
    queryset = construction_object_queryset()
    context_object_name = 'construction_object'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Obyekt detali'
    page_subtitle = 'Ish turlari va xarajatlar bo`yicha obyekt kesimi'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analytics'] = ObjectAnalyticsService.analytics_for_object(self.object)
        context['work_items'] = work_item_queryset().filter(object=self.object)
        context['expense_summaries'] = ObjectFinanceService.expense_summary_for_object(self.object)
        context['work_item_payment_form'] = context.get('work_item_payment_form') or ObjectWorkItemPaymentForm(construction_object=self.object)
        context['object_expense_form'] = context.get('object_expense_form') or ObjectExpenseForm()
        context['active_tab'] = context.get('active_tab') or self.request.GET.get('tab', 'work-items')
        context['work_item_payment_modal_open'] = context.get('work_item_payment_modal_open', False)
        context['object_expense_modal_open'] = context.get('object_expense_modal_open', False)
        context['recent_transactions'] = self.object.transactions.active().select_related('category', 'worker', 'work_item')[:10]
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Obyektlar', 'url': reverse('objects:list')},
            {'label': self.object.name, 'url': ''},
        ]
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_type = request.POST.get('form_type')

        if form_type == 'work_item_payment':
            work_item_payment_form = ObjectWorkItemPaymentForm(request.POST, request.FILES, construction_object=self.object)
            object_expense_form = ObjectExpenseForm()
            if work_item_payment_form.is_valid():
                try:
                    ObjectFinanceService.create_work_item_payment(
                        construction_object=self.object,
                        user=request.user,
                        request=request,
                        worker=work_item_payment_form.cleaned_data['worker'],
                        work_item=work_item_payment_form.cleaned_data['work_item'],
                        amount=work_item_payment_form.cleaned_data['amount'],
                        currency=work_item_payment_form.cleaned_data['currency'],
                        date=work_item_payment_form.cleaned_data['date'],
                        description=work_item_payment_form.cleaned_data['description'],
                        receipt_file=work_item_payment_form.cleaned_data['receipt_file'],
                    )
                except ValidationError as error:
                    _apply_validation_error(work_item_payment_form, error)
                else:
                    messages.success(request, 'Ish turiga to`lov qo`shildi.')
                    return redirect(f"{reverse('objects:detail', args=[self.object.pk])}?tab=work-items")
            return self.render_to_response(
                self.get_context_data(
                    work_item_payment_form=work_item_payment_form,
                    object_expense_form=object_expense_form,
                    active_tab='work-items',
                    work_item_payment_modal_open=True,
                )
            )

        if form_type == 'object_expense':
            work_item_payment_form = ObjectWorkItemPaymentForm(construction_object=self.object)
            object_expense_form = ObjectExpenseForm(request.POST, request.FILES)
            if object_expense_form.is_valid():
                try:
                    ObjectFinanceService.create_object_expense(
                        construction_object=self.object,
                        user=request.user,
                        request=request,
                        category=object_expense_form.cleaned_data['category'],
                        amount=object_expense_form.cleaned_data['amount'],
                        currency=object_expense_form.cleaned_data['currency'],
                        date=object_expense_form.cleaned_data['date'],
                        description=object_expense_form.cleaned_data['description'],
                        item_name=object_expense_form.cleaned_data['expense_item'].name if object_expense_form.cleaned_data.get('expense_item') else '',
                        quantity=object_expense_form.cleaned_data['quantity'],
                        unit=str(object_expense_form.cleaned_data['unit']) if object_expense_form.cleaned_data.get('unit') else '',
                        unit_price=object_expense_form.cleaned_data['unit_price'],
                        receipt_file=object_expense_form.cleaned_data['receipt_file'],
                    )
                except ValidationError as error:
                    _apply_validation_error(object_expense_form, error)
                else:
                    messages.success(request, 'Obyekt xarajati qo`shildi.')
                    return redirect(f"{reverse('objects:detail', args=[self.object.pk])}?tab=expenses")
            return self.render_to_response(
                self.get_context_data(
                    work_item_payment_form=work_item_payment_form,
                    object_expense_form=object_expense_form,
                    active_tab='expenses',
                    object_expense_modal_open=True,
                )
            )

        return redirect('objects:detail', pk=self.object.pk)


class ConstructionObjectExpenseCategoryDetailView(PageMetadataMixin, RoleRequiredMixin, DetailView):
    template_name = 'objects/object_expense_category_detail.html'
    queryset = construction_object_queryset()
    context_object_name = 'construction_object'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Xarajat category detali'
    page_subtitle = 'Ichki turlar, cheklar va transactionlar bo`yicha batafsil ko`rinish'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = get_object_or_404(TransactionCategory, pk=self.kwargs['category_id'])
        detail = ObjectFinanceService.expense_category_detail_for_object(self.object, category)
        context['category'] = category
        context['detail_rows'] = detail['rows']
        context['transactions'] = detail['transactions']
        context['analytics'] = ObjectAnalyticsService.analytics_for_object(self.object)
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Obyektlar', 'url': reverse('objects:list')},
            {'label': self.object.name, 'url': f"{reverse('objects:detail', args=[self.object.pk])}?tab=expenses"},
            {'label': category.name, 'url': ''},
        ]
        return context


class ConstructionObjectCreateView(PageMetadataMixin, RoleRequiredMixin, CreateView):
    template_name = 'objects/object_form.html'
    form_class = ConstructionObjectCreateForm
    success_url = reverse_lazy('objects:list')
    allowed_roles = ('ADMIN', 'DIRECTOR')
    page_title = 'Yangi obyekt'
    page_subtitle = 'Qurilish loyihasini budjet va holati bilan birga yarating'

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLogService.log_from_request(
            self.request,
            action='object_created',
            model_name='ConstructionObject',
            object_id=str(self.object.pk),
            description=f'{self.object.name} obyekt yaratildi.',
        )
        messages.success(self.request, 'Obyekt yaratildi.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Yangi obyekt'
        context['show_advanced_fields'] = False
        context['object_balance_uzs'] = '0.00'
        context['object_balance_usd'] = '0.00'
        context['balance_note'] = 'Obyekt balansi 0 dan boshlanadi. Keyin ichki company hisobidan UZS yoki USD ko`rinishida mablag` o`tkaziladi.'
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Obyektlar', 'url': reverse('objects:list')},
            {'label': 'Yangi obyekt', 'url': ''},
        ]
        return context


class ConstructionObjectUpdateView(PageMetadataMixin, RoleRequiredMixin, UpdateView):
    template_name = 'objects/object_form.html'
    form_class = ConstructionObjectUpdateForm
    queryset = ConstructionObject.objects.all()
    success_url = reverse_lazy('objects:list')
    allowed_roles = ('ADMIN', 'DIRECTOR')
    page_title = 'Obyektni tahrirlash'
    page_subtitle = 'Holat, budjet va muddatlarni yangilang'

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLogService.log_from_request(
            self.request,
            action='object_updated',
            model_name='ConstructionObject',
            object_id=str(self.object.pk),
            description=f'{self.object.name} obyekt yangilandi.',
        )
        messages.success(self.request, 'Obyekt yangilandi.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Obyektni tahrirlash'
        context['show_advanced_fields'] = True
        context['object_balance_uzs'] = self.object.balance_uzs
        context['object_balance_usd'] = self.object.balance_usd
        context['balance_note'] = 'Bu balanslar to`g`ridan-to`g`ri edit qilinmaydi. Ular company ichki o`tkazmalari orqali to`ldiriladi.'
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Obyektlar', 'url': reverse('objects:list')},
            {'label': self.object.name, 'url': reverse('objects:detail', args=[self.object.pk])},
            {'label': 'Tahrirlash', 'url': ''},
        ]
        return context


class ConstructionObjectDeleteView(PageMetadataMixin, RoleRequiredMixin, View):
    template_name = 'confirm_delete.html'
    allowed_roles = ('ADMIN',)
    page_title = 'Obyektni ochirish'
    page_subtitle = 'Bu amal audit logga yoziladi'

    def get(self, request, pk):
        instance = get_object_or_404(ConstructionObject, pk=pk)
        return render(
            request,
            self.template_name,
            {
                'form': ConfirmDeleteForm(),
                'object_label': instance.name,
                'cancel_url': reverse_lazy('objects:list'),
                'page_title': self.page_title,
                'page_subtitle': self.page_subtitle,
            },
        )

    def post(self, request, pk):
        instance = get_object_or_404(ConstructionObject, pk=pk)
        form = ConfirmDeleteForm(request.POST)
        if form.is_valid():
            name = instance.name
            instance.delete()
            AuditLogService.log_from_request(
                request,
                action='object_deleted',
                model_name='ConstructionObject',
                object_id=str(pk),
                description=f'{name} obyekt ochirildi.',
            )
            messages.success(request, 'Obyekt ochirildi.')
            return redirect('objects:list')
        return render(request, self.template_name, {'form': form, 'object_label': instance.name, 'cancel_url': reverse_lazy('objects:list')})


class WorkItemListView(PageMetadataMixin, RoleRequiredMixin, ListView):
    template_name = 'objects/work_item_list.html'
    context_object_name = 'work_items'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Ish turlari'
    page_subtitle = 'Obyekt, ishchi va kelishilgan summa bo`yicha ro`yxat'

    def get_queryset(self):
        queryset = work_item_queryset()
        object_id = self.request.GET.get('object')
        search = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        include_archived = self.request.GET.get('include_archived') == '1'
        if object_id:
            queryset = queryset.filter(object_id=object_id)
        elif not include_archived:
            queryset = queryset.exclude(object__status=ConstructionObject.Status.FINISHED)
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(object__name__icontains=search)
                | Q(assigned_worker__full_name__icontains=search)
            )
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['objects_filter'] = ConstructionObject.objects.order_by('name')
        context['status_choices'] = WorkItem.Status.choices
        context['filters'] = {
            'q': self.request.GET.get('q', ''),
            'object': self.request.GET.get('object', ''),
            'status': self.request.GET.get('status', ''),
            'include_archived': self.request.GET.get('include_archived') == '1',
        }
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Ish turlari', 'url': ''},
        ]
        return context


class WorkItemDetailView(PageMetadataMixin, RoleRequiredMixin, DetailView):
    template_name = 'objects/work_item_detail.html'
    context_object_name = 'work_item'
    queryset = work_item_queryset()
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Ish turi detali'
    page_subtitle = 'Asosiy ma`lumotlar va bog`langan to`lovlar'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paid_for_agreed_currency = self.object.paid_amount_uzs if self.object.currency == 'UZS' else self.object.paid_amount_usd
        context['remaining_amount'] = self.object.agreed_amount - paid_for_agreed_currency
        context['payment_transactions'] = self.object.transactions.active().select_related('category', 'worker')[:12]
        return context


class WorkItemCreateView(PageMetadataMixin, RoleRequiredMixin, CreateView):
    template_name = 'objects/work_item_form.html'
    form_class = WorkItemForm
    success_url = reverse_lazy('objects:work-item-list')
    allowed_roles = ('ADMIN', 'DIRECTOR')
    page_title = 'Yangi ish turi'
    page_subtitle = 'Obyekt, ishchi va kelishilgan summani kiriting'

    def get_initial(self):
        initial = super().get_initial()
        object_id = self.request.GET.get('object')
        if object_id:
            initial['object'] = object_id
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLogService.log_from_request(
            self.request,
            action='work_item_created',
            model_name='WorkItem',
            object_id=str(self.object.pk),
            description=f'{self.object.title} ish turi yaratildi.',
        )
        messages.success(self.request, 'Ish turi yaratildi.')
        return response


class WorkItemUpdateView(PageMetadataMixin, RoleRequiredMixin, UpdateView):
    template_name = 'objects/work_item_form.html'
    form_class = WorkItemForm
    queryset = WorkItem.objects.select_related('object', 'assigned_worker')
    success_url = reverse_lazy('objects:work-item-list')
    allowed_roles = ('ADMIN', 'DIRECTOR')
    page_title = 'Ish turini tahrirlash'
    page_subtitle = 'Ishchi va summa ma`lumotlarini yangilang'

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLogService.log_from_request(
            self.request,
            action='work_item_updated',
            model_name='WorkItem',
            object_id=str(self.object.pk),
            description=f'{self.object.title} ish turi yangilandi.',
        )
        messages.success(self.request, 'Ish turi yangilandi.')
        return response


class WorkItemDeleteView(PageMetadataMixin, RoleRequiredMixin, View):
    template_name = 'confirm_delete.html'
    allowed_roles = ('ADMIN',)
    page_title = 'Ish turini ochirish'
    page_subtitle = 'Tasdiqlash sahifasi orqali xavfsiz ochirish'

    def get(self, request, pk):
        instance = get_object_or_404(WorkItem, pk=pk)
        return render(
            request,
            self.template_name,
            {
                'form': ConfirmDeleteForm(),
                'object_label': instance.title,
                'cancel_url': reverse_lazy('objects:work-item-list'),
                'page_title': self.page_title,
                'page_subtitle': self.page_subtitle,
            },
        )

    def post(self, request, pk):
        instance = get_object_or_404(WorkItem, pk=pk)
        form = ConfirmDeleteForm(request.POST)
        if form.is_valid():
            title = instance.title
            instance.delete()
            AuditLogService.log_from_request(
                request,
                action='work_item_deleted',
                model_name='WorkItem',
                object_id=str(pk),
                description=f'{title} ish turi ochirildi.',
            )
            messages.success(request, 'Ish turi ochirildi.')
            return redirect('objects:work-item-list')
        return render(request, self.template_name, {'form': form, 'object_label': instance.title, 'cancel_url': reverse_lazy('objects:work-item-list')})


class ConstructionObjectStatusView(PageMetadataMixin, DirectorRequiredMixin, View):
    def post(self, request, pk):
        instance = get_object_or_404(ConstructionObject, pk=pk)
        action = request.POST.get('action')
        if action == 'finish':
            instance.status = ConstructionObject.Status.FINISHED
            instance.end_date = instance.end_date or timezone.now().date()
            message = 'Obyekt tugatildi va arxivlandi.'
            audit_action = 'object_finished'
        elif action == 'reactivate':
            instance.status = ConstructionObject.Status.ACTIVE
            instance.end_date = None
            message = 'Obyekt qayta ishga tushirildi.'
            audit_action = 'object_reactivated'
        else:
            messages.error(request, 'Nomalum obyekt amali.')
            return redirect('objects:detail', pk=instance.pk)

        instance.save(update_fields=['status', 'end_date', 'updated_at'])
        AuditLogService.log_from_request(
            request,
            action=audit_action,
            model_name='ConstructionObject',
            object_id=str(instance.pk),
            description=f'{instance.name}: {message}',
        )
        messages.success(request, message)
        return redirect('objects:detail', pk=instance.pk)


class WorkItemStatusView(PageMetadataMixin, DirectorRequiredMixin, View):
    def post(self, request, pk):
        instance = get_object_or_404(WorkItem, pk=pk)
        action = request.POST.get('action')
        if action == 'complete':
            instance.status = WorkItem.Status.COMPLETED
            instance.progress_percent = 100
            instance.end_date = instance.end_date or timezone.now().date()
            message = 'Ish turi tugallandi.'
            audit_action = 'work_item_completed'
        elif action == 'reopen':
            instance.status = WorkItem.Status.IN_PROGRESS
            instance.progress_percent = 0
            instance.end_date = None
            message = 'Ish turi qayta ishga tushirildi.'
            audit_action = 'work_item_reopened'
        else:
            messages.error(request, 'Nomalum ish turi amali.')
            return redirect('objects:work-item-detail', pk=instance.pk)

        instance.save(update_fields=['status', 'progress_percent', 'end_date', 'updated_at'])
        AuditLogService.log_from_request(
            request,
            action=audit_action,
            model_name='WorkItem',
            object_id=str(instance.pk),
            description=f'{instance.title}: {message}',
        )
        messages.success(request, message)
        next_url = request.POST.get('next') or reverse('objects:work-item-detail', args=[instance.pk])
        return redirect(next_url)
