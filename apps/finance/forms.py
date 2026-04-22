from datetime import date
from decimal import Decimal

from django import forms

from apps.core.forms import StyledFormMixin

from .models import (
    CategoryDetailModeChoices,
    CurrencyChoices,
    ExchangeRate,
    ManagerTransfer,
    Transaction,
    TransactionCategory,
    TransactionTypeChoices,
    WalletTypeChoices,
)


DEFAULT_INCOME_CATEGORY_NAME = 'Boshqa kirim'
DEFAULT_EXPENSE_CATEGORY_NAME = 'Boshqa'


class CategoryTypeSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-category-type'] = value.instance.type
        return option


class ExpenseCategorySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-detail-mode'] = value.instance.detail_mode
        return option


class ExpenseItemSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value and hasattr(value, 'instance'):
            item = value.instance
            option['attrs']['data-category-id'] = item.category_id
            option['attrs']['data-default-unit-id'] = item.default_unit_id or ''
        return option


class TransactionForm(StyledFormMixin, forms.ModelForm):
    type = forms.ChoiceField(
        choices=[
            (TransactionTypeChoices.INCOME, 'Income'),
            (TransactionTypeChoices.EXPENSE, 'Expense'),
        ]
    )

    class Meta:
        model = Transaction
        fields = (
            'type',
            'amount',
            'currency',
            'category',
            'description',
            'date',
            'object',
            'work_item',
            'worker',
            'reference_type',
            'reference_id',
        )
        widgets = {
            'date': forms.DateInput(),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'object': 'Umumiy xarajatlar uchun bo`sh qoldirish mumkin.',
            'work_item': 'Ish turi tanlansa, obyekt avtomatik bog`lanadi.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.objects.models import ConstructionObject, WorkItem
        from apps.workforce.models import Worker

        self.fields['category'].queryset = TransactionCategory.objects.filter(is_active=True).order_by('type', 'name')
        self.fields['object'].queryset = ConstructionObject.objects.order_by('name')
        self.fields['work_item'].queryset = WorkItem.objects.select_related('object').order_by('object__name', 'title')
        self.fields['worker'].queryset = Worker.objects.filter(is_active=True).order_by('full_name')


class CompanyQuickActionForm(StyledFormMixin, forms.Form):
    ACTION_COMPANY_INCOME = 'COMPANY_INCOME'
    ACTION_COMPANY_EXPENSE = 'COMPANY_EXPENSE'
    ACTION_MANAGER_TRANSFER = 'MANAGER_TRANSFER'
    ACTION_OBJECT_FUNDING = 'OBJECT_FUNDING'
    ACTION_OBJECT_RETURN = 'OBJECT_RETURN'

    action = forms.ChoiceField(
        choices=(
            (ACTION_COMPANY_INCOME, 'Ferma hisobiga kirim'),
            (ACTION_COMPANY_EXPENSE, 'Ferma hisobidan chiqim'),
            (ACTION_MANAGER_TRANSFER, 'Managerga pul o`tkazish'),
            (ACTION_OBJECT_FUNDING, 'Fermadan obyektga yo`naltirish'),
            (ACTION_OBJECT_RETURN, 'Obyektdan fermaga qaytarish'),
        ),
        label='Amal turi',
    )
    amount = forms.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal('0.01'), label='Summa')
    currency = forms.ChoiceField(choices=CurrencyChoices.choices, label='Ferma hisobidan chiqadigan valyuta')
    target_currency = forms.ChoiceField(
        required=False,
        choices=[('', 'Aylantirmasdan'), *CurrencyChoices.choices],
        label='Qabul qiluvchi valyutasi',
    )
    exchange_rate = forms.DecimalField(
        required=False,
        max_digits=18,
        decimal_places=6,
        min_value=Decimal('0.000001'),
        label='USD kursi',
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=TransactionCategory.objects.none(),
        widget=CategoryTypeSelect,
        label='Category',
    )
    manager_account = forms.ModelChoiceField(required=False, queryset=None, label='Manager')
    object = forms.ModelChoiceField(required=False, queryset=None, label='Obyekt')
    date = forms.DateField(initial=date.today, widget=forms.DateInput(attrs={'type': 'date'}), label='Sana')
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), label='Izoh')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.objects.models import ConstructionObject
        from .models import ManagerAccount

        self._ensure_default_categories()
        self.fields['action'].widget.attrs['data-company-quick-action'] = 'true'
        self.fields['category'].widget.attrs['data-company-quick-category'] = 'true'
        self.fields['manager_account'].widget.attrs['data-company-quick-manager'] = 'true'
        self.fields['target_currency'].widget.attrs['data-company-quick-target-currency'] = 'true'
        self.fields['exchange_rate'].widget.attrs['data-company-quick-exchange-rate'] = 'true'
        self.fields['object'].queryset = ConstructionObject.objects.order_by('name')
        self.fields['manager_account'].queryset = ManagerAccount.objects.select_related('user').filter(is_active=True).order_by('user__full_name')
        self.fields['category'].queryset = TransactionCategory.objects.filter(is_active=True).order_by('type', 'name')
        latest_rate = ExchangeRate.objects.filter(is_active=True).order_by('-effective_at', '-created_at').first()
        if latest_rate:
            self.fields['exchange_rate'].initial = latest_rate.usd_to_uzs
            self.fields['exchange_rate'].help_text = 'CBU kursi avtomatik olindi. Kerak bo`lsa qo`lda o`zgartiring.'
        self.fields['target_currency'].help_text = 'Bo`sh qoldirsangiz o`tkazma shu valyutada amalga oshadi.'

    @staticmethod
    def _ensure_default_categories():
        TransactionCategory.objects.get_or_create(
            name=DEFAULT_INCOME_CATEGORY_NAME,
            type=TransactionTypeChoices.INCOME,
            defaults={'description': 'Tezkor kirim uchun default category', 'is_active': True},
        )
        TransactionCategory.objects.get_or_create(
            name=DEFAULT_EXPENSE_CATEGORY_NAME,
            type=TransactionTypeChoices.EXPENSE,
            defaults={'description': 'Tezkor chiqim uchun default category', 'is_active': True},
        )

    @staticmethod
    def _default_category(transaction_type):
        name = DEFAULT_INCOME_CATEGORY_NAME if transaction_type == TransactionTypeChoices.INCOME else DEFAULT_EXPENSE_CATEGORY_NAME
        category, _ = TransactionCategory.objects.get_or_create(
            name=name,
            type=transaction_type,
            defaults={'description': 'Tezkor moliya amali uchun default category', 'is_active': True},
        )
        return category

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        construction_object = cleaned_data.get('object')
        manager_account = cleaned_data.get('manager_account')
        currency = cleaned_data.get('currency')
        target_currency = cleaned_data.get('target_currency') or currency
        exchange_rate = cleaned_data.get('exchange_rate')
        cleaned_data['target_currency'] = target_currency

        if action == self.ACTION_MANAGER_TRANSFER:
            cleaned_data['category'] = None
            cleaned_data['object'] = None
            if not manager_account:
                self.add_error('manager_account', 'Managerga pul o`tkazish uchun manager tanlang.')
            if currency != target_currency and not exchange_rate:
                self.add_error('exchange_rate', 'Valyuta aylantirish uchun kurs kiriting.')
            return cleaned_data

        if action in {self.ACTION_OBJECT_FUNDING, self.ACTION_OBJECT_RETURN}:
            cleaned_data['category'] = None
            cleaned_data['manager_account'] = None
            if not construction_object:
                self.add_error('object', 'Obyekt tanlang.')
            if action == self.ACTION_OBJECT_FUNDING and currency != target_currency and not exchange_rate:
                self.add_error('exchange_rate', 'Valyuta aylantirish uchun kurs kiriting.')
            if action == self.ACTION_OBJECT_RETURN:
                cleaned_data['target_currency'] = currency
                cleaned_data['exchange_rate'] = None
            return cleaned_data

        cleaned_data['manager_account'] = None
        if action == self.ACTION_COMPANY_INCOME:
            cleaned_data['category'] = self._default_category(TransactionTypeChoices.INCOME)
        elif action == self.ACTION_COMPANY_EXPENSE:
            if not cleaned_data.get('category'):
                self.add_error('category', 'Ferma chiqimi uchun kategoriya tanlang.')
            elif cleaned_data['category'].type != TransactionTypeChoices.EXPENSE:
                self.add_error('category', 'Ferma chiqimi uchun faqat xarajat kategoriyasi tanlanadi.')

        cleaned_data['object'] = None
        return cleaned_data


class TransactionFilterForm(StyledFormMixin, forms.Form):
    date_from = forms.DateField(required=False, label='Sana dan', widget=forms.DateInput())
    date_to = forms.DateField(required=False, label='Sana gacha', widget=forms.DateInput())
    currency = forms.ChoiceField(
        required=False,
        choices=[('', 'Barcha valyuta'), *CurrencyChoices.choices],
        label='Valyuta',
    )
    object = forms.ModelChoiceField(required=False, queryset=None, label='Obyekt')
    work_item = forms.ModelChoiceField(required=False, queryset=None, label='Ish turi')
    worker = forms.ModelChoiceField(required=False, queryset=None, label='Worker')
    manager_account = forms.ModelChoiceField(required=False, queryset=None, label='Manager hisobi')
    category = forms.ModelChoiceField(required=False, queryset=TransactionCategory.objects.none(), label='Category')
    transaction_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Barcha tur'), *TransactionTypeChoices.choices],
        label='Type',
    )
    wallet_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Barcha wallet'), *WalletTypeChoices.choices],
        label='Wallet turi',
    )
    search = forms.CharField(required=False, label='Qidiruv')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        from apps.objects.models import ConstructionObject, WorkItem
        from apps.workforce.models import Worker
        from .models import ManagerAccount

        self.fields['object'].queryset = ConstructionObject.objects.order_by('name')
        self.fields['work_item'].queryset = WorkItem.objects.select_related('object').order_by('object__name', 'title')
        self.fields['worker'].queryset = Worker.objects.filter(is_active=True).order_by('full_name')
        self.fields['category'].queryset = TransactionCategory.objects.filter(is_active=True).order_by('name')
        manager_queryset = ManagerAccount.objects.select_related('user').order_by('user__full_name')
        if user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
            manager_queryset = manager_queryset.filter(user=user)
        self.fields['manager_account'].queryset = manager_queryset


class TransactionCategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TransactionCategory
        fields = ('name', 'type', 'detail_mode', 'is_active', 'description')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].choices = [
            (TransactionTypeChoices.INCOME, 'Income'),
            (TransactionTypeChoices.EXPENSE, 'Expense'),
        ]
        self.fields['detail_mode'].choices = CategoryDetailModeChoices.choices
        self.fields['detail_mode'].help_text = 'Xarajat qo`shish modalida qaysi maydonlar chiqishini belgilaydi.'


class MeasurementUnitForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        from .models import MeasurementUnit

        model = MeasurementUnit
        fields = ('name', 'short_name', 'is_active')


class ExpenseItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        from .models import ExpenseItem

        model = ExpenseItem
        fields = ('category', 'name', 'default_unit', 'is_active', 'description')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import MeasurementUnit

        self.fields['category'].queryset = TransactionCategory.objects.filter(
            type=TransactionTypeChoices.EXPENSE,
            is_active=True,
        ).order_by('name')
        self.fields['default_unit'].queryset = MeasurementUnit.objects.filter(is_active=True).order_by('name')


class ExchangeRateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ('usd_to_uzs',)


class ManagerTransferForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ManagerTransfer
        fields = ('to_manager', 'amount', 'currency', 'description', 'date')
        widgets = {
            'date': forms.DateInput(),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import ManagerAccount

        self.fields['to_manager'].queryset = ManagerAccount.objects.select_related('user').filter(is_active=True).order_by('user__full_name')


class ManagerReturnForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ManagerTransfer
        fields = ('to_manager', 'amount', 'currency', 'description', 'date')
        widgets = {
            'date': forms.DateInput(),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        from .models import ManagerAccount

        queryset = ManagerAccount.objects.select_related('user').filter(is_active=True).order_by('user__full_name')
        if user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
            queryset = queryset.filter(user=user)
        self.fields['to_manager'].queryset = queryset


class ManagerExpenseForm(StyledFormMixin, forms.Form):
    manager_account = forms.ModelChoiceField(queryset=None, required=False, label='Manager hisobi')
    category = forms.ModelChoiceField(queryset=TransactionCategory.objects.none(), label='Category')
    amount = forms.DecimalField(max_digits=18, decimal_places=2)
    currency = forms.ChoiceField(choices=CurrencyChoices.choices)
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    date = forms.DateField(widget=forms.DateInput())
    object = forms.ModelChoiceField(required=False, queryset=None, label='Obyekt')
    work_item = forms.ModelChoiceField(required=False, queryset=None, label='Ish turi')
    worker = forms.ModelChoiceField(required=False, queryset=None, label='Worker')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        self.user = user
        super().__init__(*args, **kwargs)
        from apps.objects.models import ConstructionObject, WorkItem
        from apps.workforce.models import Worker
        from .models import ManagerAccount

        self.fields['category'].queryset = TransactionCategory.objects.filter(
            is_active=True,
            type=TransactionTypeChoices.EXPENSE,
        ).order_by('name')
        self.fields['object'].queryset = ConstructionObject.objects.order_by('name')
        self.fields['work_item'].queryset = WorkItem.objects.select_related('object').order_by('object__name', 'title')
        self.fields['worker'].queryset = Worker.objects.filter(is_active=True).order_by('full_name')
        account_queryset = ManagerAccount.objects.select_related('user').filter(is_active=True).order_by('user__full_name')
        if user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
            account_queryset = account_queryset.filter(user=user)
            self.fields['manager_account'].required = False
        self.fields['manager_account'].queryset = account_queryset

    def clean(self):
        cleaned_data = super().clean()
        manager_account = cleaned_data.get('manager_account')
        user = getattr(self, 'user', None)

        if not manager_account and user and getattr(user, 'role', '') == 'MANAGER' and not getattr(user, 'is_superuser', False):
            manager_account = getattr(user, 'manager_account', None)
            cleaned_data['manager_account'] = manager_account

        if not manager_account:
            self.add_error('manager_account', 'Manager hisobi majburiy.')

        return cleaned_data
