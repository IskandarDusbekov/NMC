from decimal import Decimal
from datetime import date

from django import forms

from apps.core.forms import StyledFormMixin, validate_receipt_file
from apps.finance.forms import ExpenseCategorySelect, ExpenseItemSelect
from apps.finance.models import CurrencyChoices, ExpenseItem, MeasurementUnit, TransactionCategory, TransactionTypeChoices
from apps.workforce.models import Worker

from .models import ConstructionObject, WorkItem


WORK_ITEM_PAYMENT_CATEGORY_NAME = 'Ish turi to`lovi'


class WorkItemSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value and hasattr(value, 'instance'):
            work_item = value.instance
            option['attrs']['data-worker-id'] = work_item.assigned_worker_id or ''
            option['attrs']['data-currency'] = work_item.currency
        return option


class ConstructionObjectCreateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ConstructionObject
        fields = (
            'name',
            'address',
            'start_date',
            'end_date',
        )
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'end_date': 'Agar loyiha ochiq bo`lsa keyinroq ham kiritish mumkin.',
        }


class ConstructionObjectUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ConstructionObject
        fields = (
            'name',
            'address',
            'description',
            'status',
            'start_date',
            'end_date',
            'budget_uzs',
            'budget_usd',
        )
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class WorkItemForm(StyledFormMixin, forms.ModelForm):
    agreed_amount = forms.DecimalField(
        required=False,
        min_value=Decimal('0.00'),
        initial=Decimal('0.00'),
        label='Kelishilgan summa',
    )

    class Meta:
        model = WorkItem
        fields = (
            'object',
            'title',
            'assigned_worker',
            'agreed_amount',
            'currency',
            'start_date',
        )
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'object': 'Obyekt',
            'title': 'Ish turi nomi',
            'assigned_worker': 'Ishchi',
            'currency': 'Valyuta',
            'start_date': 'Boshlanish sanasi',
        }
        help_texts = {
            'assigned_worker': 'Ishchini mavjud ro`yxatdan tanlang.',
            'agreed_amount': 'Bo`sh qoldirsangiz 0 bo`lib saqlanadi.',
            'currency': 'Kelishilgan summa qaysi valyutada ekanini tanlang.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_worker'].queryset = Worker.objects.filter(is_active=True).order_by('full_name')
        self.fields['assigned_worker'].required = False
        self.fields['currency'].initial = self.initial.get('currency') or self.instance.currency or CurrencyChoices.UZS
        self.fields['start_date'].initial = self.initial.get('start_date') or self.instance.start_date or date.today()

    def clean_agreed_amount(self):
        return self.cleaned_data.get('agreed_amount') or Decimal('0.00')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.assigned_worker_group = instance.assigned_worker.full_name if instance.assigned_worker else ''
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ObjectWorkItemPaymentForm(StyledFormMixin, forms.Form):
    worker = forms.ModelChoiceField(queryset=Worker.objects.none(), label='Ishchi')
    work_item = forms.ModelChoiceField(queryset=WorkItem.objects.none(), label='Ish turi', widget=WorkItemSelect)
    amount = forms.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal('0.01'), label='Summa')
    currency = forms.ChoiceField(choices=CurrencyChoices.choices, label='Valyuta')
    date = forms.DateField(initial=date.today, widget=forms.DateInput(attrs={'type': 'date'}), label='Sana')
    receipt_file = forms.FileField(required=False, label='Chek rasmi / fayl')
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), label='Izoh')

    def __init__(self, *args, construction_object, **kwargs):
        self.construction_object = construction_object
        super().__init__(*args, **kwargs)
        work_items = construction_object.work_items.select_related('assigned_worker').order_by('title')
        workers = Worker.objects.filter(work_items__object=construction_object, is_active=True).distinct().order_by('full_name')
        self.fields['worker'].queryset = workers
        self.fields['work_item'].queryset = work_items
        self.fields['currency'].initial = CurrencyChoices.UZS
        self.fields['worker'].widget.attrs['data-work-item-payment-worker'] = 'true'
        self.fields['work_item'].widget.attrs['data-work-item-payment-item'] = 'true'
        self.fields['currency'].widget.attrs['data-work-item-payment-currency'] = 'true'
        self.fields['description'].help_text = 'Masalan: avans, bajarilgan ish uchun to`lov yoki qo`shimcha izoh.'
        self.fields['currency'].help_text = 'To`lov UZS yoki USD bo`lishi mumkin. Ish turi bo`yicha ikkala valyuta alohida yig`iladi.'

    def clean(self):
        cleaned_data = super().clean()
        worker = cleaned_data.get('worker')
        work_item = cleaned_data.get('work_item')

        if work_item and work_item.object_id != self.construction_object.id:
            self.add_error('work_item', 'Ish turi shu obyektga tegishli bo`lishi kerak.')
        if worker and work_item and work_item.assigned_worker_id != worker.id:
            self.add_error('work_item', 'Tanlangan ish turi ushbu ishchiga bog`lanmagan.')

        return cleaned_data

    def clean_receipt_file(self):
        return validate_receipt_file(self.cleaned_data.get('receipt_file'))


class ObjectExpenseForm(StyledFormMixin, forms.Form):
    category = forms.ModelChoiceField(queryset=TransactionCategory.objects.none(), label='Xarajat turi', widget=ExpenseCategorySelect)
    expense_item = forms.ModelChoiceField(queryset=ExpenseItem.objects.none(), required=False, label='Ichki tur', widget=ExpenseItemSelect)
    quantity = forms.DecimalField(required=False, max_digits=14, decimal_places=3, min_value=Decimal('0.001'), label='Miqdor')
    unit = forms.ModelChoiceField(queryset=MeasurementUnit.objects.none(), required=False, label='O`lchov birligi')
    unit_price = forms.DecimalField(required=False, max_digits=18, decimal_places=2, min_value=Decimal('0.01'), label='Birlik narxi')
    amount = forms.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal('0.01'), label='Summa')
    currency = forms.ChoiceField(choices=CurrencyChoices.choices, label='Valyuta')
    date = forms.DateField(initial=date.today, widget=forms.DateInput(attrs={'type': 'date'}), label='Sana')
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), label='Izoh')
    receipt_file = forms.FileField(required=False, label='Chek rasmi / fayl')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = TransactionCategory.objects.filter(
            is_active=True,
            type=TransactionTypeChoices.EXPENSE,
        ).exclude(name=WORK_ITEM_PAYMENT_CATEGORY_NAME).order_by('name')
        self.fields['expense_item'].queryset = ExpenseItem.objects.select_related('category', 'default_unit').filter(is_active=True).order_by('category__name', 'name')
        self.fields['unit'].queryset = MeasurementUnit.objects.filter(is_active=True).order_by('name')
        self.fields['category'].help_text = 'Xarajat turlarini admin panel yoki Moliya > Category sahifasidan qo`shish mumkin.'
        self.fields['category'].widget.attrs['data-expense-category'] = 'true'
        self.fields['expense_item'].widget.attrs['data-expense-detail-field'] = 'expense_item'
        self.fields['expense_item'].widget.attrs['data-expense-item'] = 'true'
        self.fields['quantity'].widget.attrs['data-expense-detail-field'] = 'quantity'
        self.fields['unit'].widget.attrs['data-expense-detail-field'] = 'unit'
        self.fields['unit'].widget.attrs['data-expense-unit'] = 'true'
        self.fields['unit_price'].widget.attrs['data-expense-detail-field'] = 'unit_price'
        self.fields['expense_item'].help_text = 'Masalan Material ichida: Beton, Kabel, Armatura. Oziq-ovqat ichida: Non, Kartoshka.'
        self.fields['quantity'].help_text = 'Faqat material xarajatida kerak. Masalan: 32, 43, 200.'
        self.fields['unit'].help_text = 'Masalan: kub, litr, metr, kg, qop, dona.'
        self.fields['unit_price'].help_text = 'Masalan: 100000 dan. Summa alohida saqlanadi.'

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        expense_item = cleaned_data.get('expense_item')
        if category and expense_item and expense_item.category_id != category.id:
            self.add_error('expense_item', 'Ichki tur tanlangan xarajat turiga tegishli emas.')
        return cleaned_data

    def clean_receipt_file(self):
        return validate_receipt_file(self.cleaned_data.get('receipt_file'))
