from django import forms

from apps.core.forms import StyledFormMixin


class TelegramMiniAppForm(StyledFormMixin, forms.Form):
    init_data = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label='Telegram initData')
