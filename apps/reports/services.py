from __future__ import annotations

from django.http import HttpResponse
from django.utils.html import escape


class ReportExportService:
    @staticmethod
    def export_transactions_excel(queryset):
        totals = {}
        category_totals = {}
        object_totals = {}
        rows = [
            '<tr>'
            '<th>Sana</th><th>Amal</th><th>Hisob</th><th>Xarajat turi</th><th>Detal</th>'
            '<th>Miqdor</th><th>Birlik</th><th>Birlik narx</th><th>Summa</th><th>Valyuta</th>'
            '<th>Obyekt</th><th>Ish turi</th><th>Ishchi</th><th>Manba</th><th>Izoh</th>'
            '</tr>'
        ]
        for item in queryset:
            sign_amount = item.amount * item.sign
            totals[(item.type, item.currency)] = totals.get((item.type, item.currency), 0) + sign_amount
            if item.category:
                category_totals[(item.category.name, item.currency)] = category_totals.get((item.category.name, item.currency), 0) + item.amount
            if item.object:
                object_totals[(item.object.name, item.currency)] = object_totals.get((item.object.name, item.currency), 0) + item.amount
            rows.append(
                '<tr>'
                f'<td>{escape(item.date)}</td>'
                f'<td>{escape(item.get_entry_type_display())}</td>'
                f'<td>{escape(item.get_wallet_type_display())}</td>'
                f'<td>{escape(item.category.name if item.category else "Ichki transfer")}</td>'
                f'<td>{escape(item.item_name)}</td>'
                f'<td>{escape(item.quantity or "")}</td>'
                f'<td>{escape(item.unit)}</td>'
                f'<td>{escape(item.unit_price or "")}</td>'
                f'<td>{escape(item.amount)}</td>'
                f'<td>{escape(item.currency)}</td>'
                f'<td>{escape(item.object.name if item.object else "")}</td>'
                f'<td>{escape(item.work_item.title if item.work_item else "")}</td>'
                f'<td>{escape(item.worker.full_name if item.worker else "")}</td>'
                f'<td>{escape(item.get_source_display())}</td>'
                f'<td>{escape(item.description)}</td>'
                '</tr>'
            )
        summary_rows = [
            '<tr><th>Bo`lim</th><th>Nomi</th><th>Valyuta</th><th>Jami</th></tr>'
        ]
        for (transaction_type, currency), total in totals.items():
            summary_rows.append(f'<tr><td>Umumiy</td><td>{escape(transaction_type)}</td><td>{escape(currency)}</td><td>{escape(total)}</td></tr>')
        for (category, currency), total in category_totals.items():
            summary_rows.append(f'<tr><td>Category</td><td>{escape(category)}</td><td>{escape(currency)}</td><td>{escape(total)}</td></tr>')
        for (object_name, currency), total in object_totals.items():
            summary_rows.append(f'<tr><td>Obyekt</td><td>{escape(object_name)}</td><td>{escape(currency)}</td><td>{escape(total)}</td></tr>')
        content = (
            '<html><head><meta charset="utf-8">'
            '<style>body{{font-family:Arial,sans-serif}} table{{border-collapse:collapse;margin-bottom:24px}}'
            'th{{background:#0f172a;color:#fff;font-weight:700}} th,td{{border:1px solid #cbd5e1;padding:8px 10px}}'
            '.title{{font-size:20px;font-weight:700;margin:12px 0}}</style></head>'
            '<body><div class="title">Umumiy hisobot</div><table>{summary}</table>'
            '<div class="title">Transactionlar</div><table>{rows}</table></body></html>'
        ).format(summary=''.join(summary_rows), rows=''.join(rows))
        response = HttpResponse(content, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="umumiy-hisobot.xls"'
        return response
