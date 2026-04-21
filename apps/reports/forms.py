from django import forms

from apps.core.forms import StyledFormMixin
from apps.finance.models import CurrencyChoices, TransactionCategory, TransactionTypeChoices


class ReportFilterForm(StyledFormMixin, forms.Form):
    date_from = forms.DateField(required=False, label='Sana dan', widget=forms.DateInput())
    date_to = forms.DateField(required=False, label='Sana gacha', widget=forms.DateInput())
    currency = forms.ChoiceField(required=False, choices=[('', 'Barcha'), *CurrencyChoices.choices])
    object = forms.ModelChoiceField(required=False, queryset=None, label='Obyekt')
    worker = forms.ModelChoiceField(required=False, queryset=None, label='Worker')
    category = forms.ModelChoiceField(required=False, queryset=TransactionCategory.objects.none(), label='Category')
    transaction_type = forms.ChoiceField(required=False, choices=[('', 'Barcha'), *TransactionTypeChoices.choices], label='Type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.objects.models import ConstructionObject
        from apps.workforce.models import Worker

        self.fields['object'].queryset = ConstructionObject.objects.order_by('name')
        self.fields['worker'].queryset = Worker.objects.filter(is_active=True).order_by('full_name')
        self.fields['category'].queryset = TransactionCategory.objects.filter(is_active=True).order_by('name')
