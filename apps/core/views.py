from __future__ import annotations

from django.db.models import Q
from django.shortcuts import redirect, render
from django.views import View

from apps.core.mixins import RoleRequiredMixin


class GlobalSearchView(RoleRequiredMixin, View):
    """
    Barcha modellarda qidirish.
    GET /search/?q=...
    """
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER')

    def get(self, request):
        query = (request.GET.get('q') or '').strip()
        results = {
            'objects': [],
            'workers': [],
            'transactions': [],
            'work_items': [],
            'salary_payments': [],
        }
        total = 0

        if query:
            from apps.objects.models import ConstructionObject, WorkItem
            from apps.workforce.models import Worker, SalaryPayment
            from apps.finance.models import Transaction

            # Objects
            obj_qs = ConstructionObject.objects.filter(
                Q(name__icontains=query) | Q(address__icontains=query)
            )[:10]
            results['objects'] = list(obj_qs)
            total += len(results['objects'])

            # Workers
            wkr_qs = Worker.objects.filter(
                Q(full_name__icontains=query) | Q(notes__icontains=query)
            )[:10]
            results['workers'] = list(wkr_qs)
            total += len(results['workers'])

            # Work items
            wi_qs = WorkItem.objects.filter(
                Q(title__icontains=query) | Q(assigned_worker_group__icontains=query)
            ).select_related('object')[:10]
            results['work_items'] = list(wi_qs)
            total += len(results['work_items'])

            # Transactions
            tx_qs = Transaction.objects.active().filter(
                Q(item_name__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query)
            ).select_related('category', 'object', 'manager_account__user')
            if hasattr(request.user, 'role') and request.user.role == 'MANAGER' and not request.user.is_superuser:
                tx_qs = tx_qs.filter(manager_account=getattr(request.user, 'manager_account', None))
            results['transactions'] = list(tx_qs[:10])
            total += len(results['transactions'])

            # Salary payments
            sp_qs = SalaryPayment.objects.filter(
                Q(worker__full_name__icontains=query) | Q(description__icontains=query)
            ).select_related('worker', 'object')[:10]
            results['salary_payments'] = list(sp_qs)
            total += len(results['salary_payments'])

        return render(request, 'core/search_results.html', {
            'query': query,
            'results': results,
            'total': total,
            'page_title': f'Qidiruv: {query}' if query else 'Global qidiruv',
        })


def home_redirect(request):
    return redirect('dashboard:index')
