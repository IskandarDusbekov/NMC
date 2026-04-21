from django import forms

from apps.core.forms import StyledFormMixin
from apps.finance.models import WalletTypeChoices

from .models import SalaryPayment, Worker


class WorkerForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Worker
        fields = (
            'full_name',
            'worker_type',
            'monthly_salary',
            'salary_currency',
            'is_active',
            'notes',
        )
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].label = 'Full name'
        self.fields['worker_type'].label = 'Ishchi turi'
        self.fields['monthly_salary'].label = 'Oylik summa'
        self.fields['salary_currency'].label = 'Oylik valyutasi'
        self.fields['notes'].label = 'Izoh'
        self.fields['monthly_salary'].required = False
        self.fields['salary_currency'].required = False
        self.fields['worker_type'].widget.attrs['data-worker-type-input'] = 'true'
        self.fields['monthly_salary'].widget.attrs['data-worker-monthly-input'] = 'true'
        self.fields['salary_currency'].widget.attrs['data-worker-monthly-currency'] = 'true'

    def clean(self):
        cleaned_data = super().clean()
        worker_type = cleaned_data.get('worker_type')
        monthly_salary = cleaned_data.get('monthly_salary')
        salary_currency = cleaned_data.get('salary_currency')
        if worker_type == Worker.WorkerType.BRIGADE:
            cleaned_data['monthly_salary'] = None
            cleaned_data['salary_currency'] = ''
        elif worker_type == Worker.WorkerType.MONTHLY:
            if monthly_salary is None:
                self.add_error('monthly_salary', 'Oylik ishchi uchun oylik summa majburiy.')
            if not salary_currency:
                self.add_error('salary_currency', 'Oylik ishchi uchun valyuta tanlang.')
        return cleaned_data


class SalaryPaymentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SalaryPayment
        fields = ('worker', 'amount', 'currency', 'date', 'source_wallet', 'manager_account', 'object', 'description')
        widgets = {
            'date': forms.DateInput(),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        self.user = user
        super().__init__(*args, **kwargs)
        from apps.objects.models import ConstructionObject
        from apps.finance.models import ManagerAccount

        self.fields['worker'].queryset = Worker.objects.filter(is_active=True).order_by('full_name')
        self.fields['object'].queryset = ConstructionObject.objects.order_by('name')
        manager_queryset = ManagerAccount.objects.select_related('user').filter(is_active=True).order_by('user__full_name')
        if user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
            manager_queryset = manager_queryset.filter(user=user)
        self.fields['manager_account'].queryset = manager_queryset

    def clean(self):
        cleaned_data = super().clean()
        source_wallet = cleaned_data.get('source_wallet')
        manager_account = cleaned_data.get('manager_account')
        user = getattr(self, 'user', None)

        if source_wallet == WalletTypeChoices.MANAGER:
            if not manager_account and user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
                manager_account = getattr(user, 'manager_account', None)
                cleaned_data['manager_account'] = manager_account
            if not manager_account:
                self.add_error('manager_account', 'Manager wallet tanlansa manager hisobi majburiy.')
        else:
            cleaned_data['manager_account'] = None

        return cleaned_data
