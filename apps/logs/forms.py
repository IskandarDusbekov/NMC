from django import forms

from apps.core.forms import StyledFormMixin


class AuditLogFilterForm(StyledFormMixin, forms.Form):
    action = forms.CharField(required=False, label='Action')
    model_name = forms.CharField(required=False, label='Model')
