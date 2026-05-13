from django import forms


ALLOWED_RECEIPT_CONTENT_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'application/pdf',
}
MAX_RECEIPT_FILE_SIZE = 5 * 1024 * 1024


def validate_receipt_file(file):
    if not file:
        return file
    if file.size > MAX_RECEIPT_FILE_SIZE:
        raise forms.ValidationError('Fayl hajmi 5 MB dan oshmasligi kerak.')
    content_type = getattr(file, 'content_type', '')
    if content_type and content_type not in ALLOWED_RECEIPT_CONTENT_TYPES:
        raise forms.ValidationError('Faqat JPG, PNG, WEBP yoki PDF fayl yuklash mumkin.')
    return file


class StyledFormMixin:
    input_class = (
        'mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 '
        'text-sm text-slate-900 shadow-sm outline-none transition-all '
        'placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 '
        'hover:border-slate-300'
    )
    checkbox_class = 'h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500'
    select_class = (
        'mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 '
        'text-sm text-slate-900 shadow-sm transition-all cursor-pointer '
        'focus:border-blue-500 focus:ring-2 focus:ring-blue-100 hover:border-slate-300'
    )
    textarea_class = (
        'mt-1.5 block min-h-24 w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 '
        'text-sm text-slate-900 shadow-sm transition-all resize-y '
        'focus:border-blue-500 focus:ring-2 focus:ring-blue-100 hover:border-slate-300'
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
