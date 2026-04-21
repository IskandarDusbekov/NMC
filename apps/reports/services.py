from __future__ import annotations

from django.http import HttpResponse
from django.utils.html import escape


class ReportExportService:
    @staticmethod
    def export_transactions_excel(queryset):
        rows = [
            '<tr>'
            '<th>Date</th><th>Type</th><th>Amount</th><th>Currency</th><th>Category</th><th>Object</th><th>Worker</th><th>Description</th>'
            '</tr>'
        ]
        for item in queryset:
            rows.append(
                '<tr>'
                f'<td>{escape(item.date)}</td>'
                f'<td>{escape(item.type)}</td>'
                f'<td>{escape(item.amount)}</td>'
                f'<td>{escape(item.currency)}</td>'
                f'<td>{escape(item.category.name if item.category else "")}</td>'
                f'<td>{escape(item.object.name if item.object else "")}</td>'
                f'<td>{escape(item.worker.full_name if item.worker else "")}</td>'
                f'<td>{escape(item.description)}</td>'
                '</tr>'
            )
        content = (
            '<html><head><meta charset="utf-8"></head>'
            '<body><table border="1">{rows}</table></body></html>'
        ).format(rows=''.join(rows))
        response = HttpResponse(content, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="transaction-report.xls"'
        return response
