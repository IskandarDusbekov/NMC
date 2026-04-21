from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, TemplateView, UpdateView

from apps.core.forms import ConfirmDeleteForm
from apps.core.mixins import DirectorRequiredMixin, PageMetadataMixin, RoleRequiredMixin

from .forms import (
    CompanyQuickActionForm,
    ExchangeRateForm,
    ManagerExpenseForm,
    ManagerReturnForm,
    ManagerTransferForm,
    TransactionCategoryForm,
    TransactionFilterForm,
    TransactionForm,
)
from .models import ExchangeRate, Transaction, TransactionCategory, WalletTypeChoices
from .selectors import (
    category_summary,
    daily_expense_series,
    manager_accounts,
    monthly_expense_series,
    recent_transfers,
    top_manager_spending,
    transaction_list,
)
from .services import (
    CompanyBalanceService,
    CompanyQuickActionService,
    ExchangeRateService,
    ManagerBalanceService,
    ManagerExpenseService,
    TransactionService,
    TransferService,
)


def _apply_validation_error(form, error: ValidationError):
    if hasattr(error, 'message_dict'):
        for field, messages in error.message_dict.items():
            for message in messages:
                if field == '__all__':
                    form.add_error(None, message)
                else:
                    form.add_error(field, message)
    else:
        for message in error.messages:
            form.add_error(None, message)


class TransactionListView(PageMetadataMixin, RoleRequiredMixin, ListView):
    template_name = 'finance/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Moliya ledger'
    page_subtitle = 'Ferma va manager wallet harakatlarini bitta markaziy jurnal orqali ko`ring'

    def get_queryset(self):
        self.filter_form = TransactionFilterForm(self.request.GET or None, user=self.request.user)
        if self.filter_form.is_valid():
            return transaction_list(self.filter_form.cleaned_data, user=self.request.user)
        return transaction_list(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        context['quick_action_form'] = context.get('quick_action_form') or CompanyQuickActionForm()
        context['quick_action_modal_open'] = context.get('quick_action_modal_open', False)
        context['category_distribution'] = category_summary(user=self.request.user)
        context['daily_expense_series'] = daily_expense_series(user=self.request.user)
        context['monthly_expense_series'] = monthly_expense_series(user=self.request.user)
        context['company_balances'] = CompanyBalanceService.summary()
        if getattr(self.request.user, 'role', '') == 'MANAGER' and hasattr(self.request.user, 'manager_account'):
            context['manager_balances'] = ManagerBalanceService.summary_for_account(self.request.user.manager_account)
        context['recent_transfers'] = recent_transfers(user=self.request.user)
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Moliya', 'url': ''},
        ]
        if getattr(self.request.user, 'role', '') == 'MANAGER' and not getattr(self.request.user, 'is_superuser', False):
            context['page_title'] = 'Mening ledgerim'
            context['page_subtitle'] = 'Faqat o`zimga tegishli manager wallet harakatlari'
        return context

    def post(self, request, *args, **kwargs):
        if getattr(request.user, 'role', '') == 'MANAGER' and not getattr(request.user, 'is_superuser', False):
            return redirect('finance:transaction-list')
        form = CompanyQuickActionForm(request.POST)
        self.object_list = self.get_queryset()
        if form.is_valid():
            try:
                CompanyQuickActionService.execute(
                    user=request.user,
                    request=request,
                    action=form.cleaned_data['action'],
                    amount=form.cleaned_data['amount'],
                    currency=form.cleaned_data['currency'],
                    category=form.cleaned_data['category'],
                    manager_account=form.cleaned_data['manager_account'],
                    object=form.cleaned_data['object'],
                    date=form.cleaned_data['date'],
                    description=form.cleaned_data['description'],
                    target_currency=form.cleaned_data.get('target_currency'),
                    exchange_rate=form.cleaned_data.get('exchange_rate'),
                )
            except ValidationError as error:
                _apply_validation_error(form, error)
            else:
                messages.success(request, 'Moliya amali saqlandi.')
                return redirect('finance:transaction-list')
        context = self.get_context_data(object_list=self.object_list)
        context['quick_action_form'] = form
        context['quick_action_modal_open'] = True
        return self.render_to_response(context)


class TransactionCreateView(PageMetadataMixin, DirectorRequiredMixin, FormView):
    template_name = 'finance/transaction_form.html'
    form_class = TransactionForm
    success_url = reverse_lazy('finance:transaction-list')
    page_title = 'Ferma transaction yaratish'
    page_subtitle = 'Faqat ferma wallet uchun kirim yoki chiqim yaratiladi'

    def form_valid(self, form):
        try:
            TransactionService.create_transaction(
                user=self.request.user,
                request=self.request,
                wallet_type=WalletTypeChoices.COMPANY,
                manager_account=None,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _apply_validation_error(form, error)
            return self.form_invalid(form)
        messages.success(self.request, 'Ferma transaction muvaffaqiyatli yaratildi.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Ferma transaction'
        return context


class TransactionUpdateView(PageMetadataMixin, DirectorRequiredMixin, UpdateView):
    template_name = 'finance/transaction_form.html'
    form_class = TransactionForm
    queryset = Transaction.objects.active().select_related('category', 'object', 'work_item', 'worker', 'manager_account').exclude(type='TRANSFER')
    success_url = reverse_lazy('finance:transaction-list')
    page_title = 'Transactionni tahrirlash'
    page_subtitle = 'Transfer yozuvlari servis orqali boshqariladi, qo`lda edit qilinmaydi'

    def form_valid(self, form):
        try:
            TransactionService.update_transaction(
                self.object,
                user=self.request.user,
                request=self.request,
                wallet_type=self.object.wallet_type,
                manager_account=self.object.manager_account,
                entry_type=self.object.entry_type,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _apply_validation_error(form, error)
            return self.form_invalid(form)
        messages.success(self.request, 'Transaction yangilandi.')
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Transactionni yangilash'
        return context


class TransactionDeleteView(PageMetadataMixin, DirectorRequiredMixin, View):
    template_name = 'confirm_delete.html'
    page_title = 'Transactionni ochirish'
    page_subtitle = 'Soft delete audit log bilan yoziladi'

    def get(self, request, pk):
        transaction = get_object_or_404(Transaction.objects.active(), pk=pk)
        return render(
            request,
            self.template_name,
            {
                'form': ConfirmDeleteForm(),
                'page_title': self.page_title,
                'page_subtitle': self.page_subtitle,
                'object_label': f'{transaction.entry_type} - {transaction.amount} {transaction.currency}',
                'cancel_url': reverse_lazy('finance:transaction-list'),
            },
        )

    def post(self, request, pk):
        transaction = get_object_or_404(Transaction.objects.active(), pk=pk)
        form = ConfirmDeleteForm(request.POST)
        if form.is_valid():
            try:
                TransactionService.soft_delete_transaction(transaction, user=request.user, request=request)
            except ValidationError as error:
                messages.error(request, '; '.join(error.messages if hasattr(error, 'messages') else [str(error)]))
                return redirect('finance:transaction-list')
            messages.success(request, 'Transaction ochirildi. Bog`liq ledger yozuvlari ham xavfsiz yangilandi.')
            return redirect('finance:transaction-list')
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'page_title': self.page_title,
                'page_subtitle': self.page_subtitle,
                'object_label': str(transaction),
                'cancel_url': reverse_lazy('finance:transaction-list'),
            },
        )


class ManagerAccountListView(PageMetadataMixin, RoleRequiredMixin, TemplateView):
    template_name = 'finance/manager_account_list.html'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Manager hisoblari'
    page_subtitle = 'Har bir manager uchun alohida operatsion wallet balansi'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []
        for account in manager_accounts(self.request.user):
            rows.append(
                {
                    'account': account,
                    'balances': ManagerBalanceService.summary_for_account(account),
                }
            )
        context['account_rows'] = rows
        is_manager_view = getattr(self.request.user, 'role', '') == 'MANAGER' and not getattr(self.request.user, 'is_superuser', False)
        context['is_manager_view'] = is_manager_view
        context['personal_balances'] = rows[0]['balances'] if is_manager_view and rows else None
        context['company_balances'] = CompanyBalanceService.summary() if not is_manager_view else None
        context['manager_holdings'] = ManagerBalanceService.total_manager_holdings() if not is_manager_view else None
        context['recent_transfers'] = recent_transfers(user=self.request.user)
        context['top_manager_spending'] = top_manager_spending() if not is_manager_view else []
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Manager hisoblari' if not is_manager_view else 'Mening hisobim', 'url': ''},
        ]
        if is_manager_view:
            context['page_title'] = 'Mening hisobim'
            context['page_subtitle'] = 'Menga biriktirilgan operatsion wallet balansi va transferlar tarixi'
        return context


class ManagerTransferCreateView(PageMetadataMixin, DirectorRequiredMixin, FormView):
    template_name = 'finance/manager_transfer_form.html'
    form_class = ManagerTransferForm
    success_url = reverse_lazy('finance:manager-account-list')
    page_title = 'Managerga pul o`tkazish'
    page_subtitle = 'Ferma balansidan manager operatsion hisobiga ichki transfer'

    def form_valid(self, form):
        try:
            TransferService.transfer_to_manager(
                manager_account=form.cleaned_data['to_manager'],
                amount=form.cleaned_data['amount'],
                currency=form.cleaned_data['currency'],
                description=form.cleaned_data['description'],
                date=form.cleaned_data['date'],
                user=self.request.user,
                request=self.request,
            )
        except ValidationError as error:
            _apply_validation_error(form, error)
            return self.form_invalid(form)
        messages.success(self.request, 'Managerga pul o`tkazildi.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Manager hisoblari', 'url': reverse_lazy('finance:manager-account-list')},
            {'label': 'Transfer', 'url': ''},
        ]
        return context


class ManagerReturnCreateView(PageMetadataMixin, RoleRequiredMixin, FormView):
    template_name = 'finance/manager_return_form.html'
    form_class = ManagerReturnForm
    success_url = reverse_lazy('finance:manager-account-list')
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Manager mablag`ini qaytarish'
    page_subtitle = 'Ishlatilmagan operatsion mablag`ni ferma hisobiga qaytarish'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            TransferService.return_to_company(
                manager_account=form.cleaned_data['to_manager'],
                amount=form.cleaned_data['amount'],
                currency=form.cleaned_data['currency'],
                description=form.cleaned_data['description'],
                date=form.cleaned_data['date'],
                user=self.request.user,
                request=self.request,
            )
        except ValidationError as error:
            _apply_validation_error(form, error)
            return self.form_invalid(form)
        messages.success(self.request, 'Mablag` ferma hisobiga qaytarildi.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'label': 'Dashboard', 'url': '/dashboard/'},
            {'label': 'Manager hisoblari', 'url': reverse_lazy('finance:manager-account-list')},
            {'label': 'Return', 'url': ''},
        ]
        return context


class ManagerExpenseCreateView(PageMetadataMixin, RoleRequiredMixin, View):
    template_name = 'finance/manager_expense_form.html'
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')
    page_title = 'Manager expense'
    page_subtitle = 'Xarajat manager walletdan ayriladi va ferma balansiga qayta ta`sir qilmaydi'

    def _build_context(self, request, form):
        context = {
            'form': form,
            'page_title': self.page_title,
            'page_subtitle': self.page_subtitle,
            'breadcrumbs': [
                {'label': 'Dashboard', 'url': '/dashboard/'},
                {'label': 'Moliya', 'url': reverse_lazy('finance:transaction-list')},
                {'label': 'Manager expense', 'url': ''},
            ],
        }
        if getattr(request.user, 'role', '') == 'MANAGER' and not getattr(request.user, 'is_superuser', False):
            context['page_title'] = 'Mening xarajatim'
            context['page_subtitle'] = 'Xarajat faqat mening operatsion walletimdan ayriladi'
        return context

    def get(self, request):
        return render(request, self.template_name, self._build_context(request, ManagerExpenseForm(user=request.user)))

    def post(self, request):
        form = ManagerExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            manager_account = form.cleaned_data['manager_account'] or getattr(request.user, 'manager_account', None)
            try:
                ManagerExpenseService.create_expense(
                    manager_account=manager_account,
                    category=form.cleaned_data['category'],
                    amount=form.cleaned_data['amount'],
                    currency=form.cleaned_data['currency'],
                    description=form.cleaned_data['description'],
                    date=form.cleaned_data['date'],
                    object=form.cleaned_data['object'],
                    work_item=form.cleaned_data['work_item'],
                    worker=form.cleaned_data['worker'],
                    user=request.user,
                    request=request,
                )
            except ValidationError as error:
                _apply_validation_error(form, error)
                return render(request, self.template_name, self._build_context(request, form))
            messages.success(request, 'Manager expense yaratildi.')
            return redirect('finance:transaction-list')
        return render(request, self.template_name, self._build_context(request, form))


class CategoryManagementView(PageMetadataMixin, DirectorRequiredMixin, View):
    template_name = 'finance/category_list.html'
    page_title = 'Category boshqaruvi'
    page_subtitle = 'Kirim va chiqim kategoriyalarini markaziy tarzda boshqaring'

    def _build_context(self, *, form, categories):
        return {
            'form': form,
            'categories': categories,
            'page_title': self.page_title,
            'page_subtitle': self.page_subtitle,
            'breadcrumbs': [
                {'label': 'Dashboard', 'url': '/dashboard/'},
                {'label': 'Moliya', 'url': reverse_lazy('finance:transaction-list')},
                {'label': 'Category', 'url': ''},
            ],
        }

    def get(self, request):
        categories = TransactionCategory.objects.exclude(type='TRANSFER').order_by('type', 'name')
        return render(request, self.template_name, self._build_context(form=TransactionCategoryForm(), categories=categories))

    def post(self, request):
        form = TransactionCategoryForm(request.POST)
        categories = TransactionCategory.objects.exclude(type='TRANSFER').order_by('type', 'name')
        if form.is_valid():
            form.save()
            messages.success(request, 'Category saqlandi.')
            return redirect('finance:category-list')
        return render(request, self.template_name, self._build_context(form=form, categories=categories))


class ExchangeRateManagementView(PageMetadataMixin, DirectorRequiredMixin, View):
    template_name = 'finance/exchange_rate_list.html'
    page_title = 'USD kursi'
    page_subtitle = 'Header va hisobotlarda ishlatiladigan markaziy kurs'

    def _build_context(self, *, form, rates):
        return {
            'form': form,
            'rates': rates,
            'page_title': self.page_title,
            'page_subtitle': self.page_subtitle,
            'breadcrumbs': [
                {'label': 'Dashboard', 'url': '/dashboard/'},
                {'label': 'Moliya', 'url': reverse_lazy('finance:transaction-list')},
                {'label': 'USD kursi', 'url': ''},
            ],
        }

    def get(self, request):
        rates = ExchangeRate.objects.order_by('-effective_at')[:10]
        return render(request, self.template_name, self._build_context(form=ExchangeRateForm(), rates=rates))

    def post(self, request):
        if request.POST.get('source') == 'cbu':
            try:
                ExchangeRateService.update_rate_from_cbu(user=request.user)
            except ValidationError as error:
                messages.error(request, '; '.join(error.messages if hasattr(error, 'messages') else [str(error)]))
            else:
                messages.success(request, 'USD kursi CBU API orqali yangilandi.')
            return redirect('finance:exchange-rate-list')

        form = ExchangeRateForm(request.POST)
        if form.is_valid():
            ExchangeRateService.update_rate(usd_to_uzs=form.cleaned_data['usd_to_uzs'], user=request.user)
            messages.success(request, 'USD kursi yangilandi.')
            return redirect('finance:exchange-rate-list')
        rates = ExchangeRate.objects.order_by('-effective_at')[:10]
        return render(request, self.template_name, self._build_context(form=form, rates=rates))
