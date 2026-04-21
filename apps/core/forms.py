from django import forms


class StyledFormMixin:
    input_class = (
        'mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 '
        'text-sm text-slate-900 shadow-sm outline-none transition '
        'placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100'
    )
    checkbox_class = 'h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500'
    select_class = (
        'mt-2 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 '
        'text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:ring-2 focus:ring-sky-100'
    )
    textarea_class = (
        'mt-2 block min-h-28 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 '
        'text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:ring-2 focus:ring-sky-100'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = self.checkbox_class
                continue
            if isinstance(widget, forms.Select):
                widget.attrs['class'] = self.select_class
            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = self.textarea_class
            else:
                widget.attrs['class'] = self.input_class
            if isinstance(widget, forms.DateInput):
                widget.attrs['type'] = 'date'


class ConfirmDeleteForm(StyledFormMixin, forms.Form):
    confirmation = forms.CharField(
        label='Tasdiqlash',
        help_text='Ochirishni davom ettirish uchun DELETE deb yozing.',
    )

    def clean_confirmation(self):
        value = self.cleaned_data['confirmation'].strip().upper()
        if value != 'DELETE':
            raise forms.ValidationError('Tasdiqlash uchun DELETE deb yozing.')
        return value
