from __future__ import annotations

import mimetypes
from pathlib import Path

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

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


def about_view(request):
    """Ferma haqida — standalone mini app sahifasi."""
    return render(request, 'core/about.html')


# ══════════════════════════════════════════════════════════════════════════════
#  Fayl arxivi
# ══════════════════════════════════════════════════════════════════════════════

class FileListView(RoleRequiredMixin, View):
    """Barcha fayllar ro'yxati — filter va qidiruv bilan."""
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER')

    def get(self, request):
        from apps.core.models import ProjectFile
        from apps.objects.models import ConstructionObject

        qs = ProjectFile.objects.select_related('object', 'uploaded_by')

        # MANAGER faqat o'zi yuklagan yoki uning obyektlariga tegishli fayllarni ko'radi
        role = getattr(request.user, 'role', '')
        if role == 'MANAGER' and not request.user.is_superuser:
            qs = qs.filter(
                Q(uploaded_by=request.user) | Q(object__isnull=True)
            )

        # ── Filtrlar ──
        q       = (request.GET.get('q') or '').strip()
        cat     = request.GET.get('category') or ''
        obj_id  = request.GET.get('object') or ''
        ext     = request.GET.get('ext') or ''

        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(original_filename__icontains=q)
            )
        if cat:
            qs = qs.filter(category=cat)
        if obj_id:
            qs = qs.filter(object_id=obj_id)
        if ext:
            qs = qs.filter(file_ext=ext)

        # ── Pagination ──
        paginator = Paginator(qs, 20)
        page      = paginator.get_page(request.GET.get('page'))

        objects   = ConstructionObject.objects.order_by('name')
        exts      = (
            ProjectFile.objects.values_list('file_ext', flat=True)
            .distinct().order_by('file_ext')
        )

        return render(request, 'core/file_list.html', {
            'page_obj':   page,
            'files':      page.object_list,
            'q':          q,
            'cat':        cat,
            'obj_id':     obj_id,
            'ext':        ext,
            'categories': ProjectFile.Category.choices,
            'objects':    objects,
            'exts':       [e for e in exts if e],
            'total':      qs.count(),
            'page_title': 'Fayl arxivi',
            'breadcrumbs': [{'label': 'Fayl arxivi', 'url': ''}],
        })


class FileUploadView(RoleRequiredMixin, View):
    """Fayl yuklash."""
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')

    def get(self, request):
        from apps.objects.models import ConstructionObject
        from apps.core.models import ProjectFile
        objects = ConstructionObject.objects.order_by('name')
        return render(request, 'core/file_upload.html', {
            'objects':    objects,
            'categories': ProjectFile.Category.choices,
            'page_title': 'Fayl yuklash',
            'breadcrumbs': [
                {'label': 'Fayl arxivi', 'url': '/files/'},
                {'label': 'Yuklash', 'url': ''},
            ],
        })

    def post(self, request):
        from apps.core.models import ProjectFile, _validate_project_file

        title    = (request.POST.get('title') or '').strip()
        category = request.POST.get('category') or 'other'
        desc     = (request.POST.get('description') or '').strip()
        obj_id   = request.POST.get('object') or None
        file     = request.FILES.get('file')

        errors = []
        if not title:
            errors.append('Sarlavha majburiy.')
        if not file:
            errors.append('Fayl tanlanmagan.')
        else:
            try:
                _validate_project_file(file)
            except Exception as exc:
                errors.append(str(exc))

        if errors:
            from apps.objects.models import ConstructionObject
            return render(request, 'core/file_upload.html', {
                'objects':    ConstructionObject.objects.order_by('name'),
                'categories': ProjectFile.Category.choices,
                'errors':     errors,
                'post':       request.POST,
                'page_title': 'Fayl yuklash',
            })

        pf = ProjectFile(
            title=title,
            category=category,
            description=desc,
            uploaded_by=request.user,
            file=file,
        )
        if obj_id:
            from apps.objects.models import ConstructionObject
            pf.object = ConstructionObject.objects.filter(pk=obj_id).first()
        pf.save()

        messages.success(request, f'"{title}" fayli muvaffaqiyatli yuklandi.')
        return redirect('core:file-list')


@method_decorator(never_cache, name='dispatch')
class FileDownloadView(RoleRequiredMixin, View):
    """
    Xavfsiz fayl yuklab olish.
    Fayllar to'g'ridan-to'g'ri /media/ URL orqali emas,
    shu view orqali beriladi — ruxsat tekshiruvi bilan.
    """
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER', 'OBSERVER')

    def get(self, request, uid):
        from apps.core.models import ProjectFile
        pf = get_object_or_404(ProjectFile, uid=uid)

        # MANAGER faqat o'zi yuklagan yoki umumiy fayllarni ola oladi
        role = getattr(request.user, 'role', '')
        if role == 'MANAGER' and not request.user.is_superuser:
            if pf.uploaded_by != request.user and pf.object is not None:
                return HttpResponseForbidden('Bu faylni ko`rish uchun ruxsat yo`q.')

        try:
            file_handle = pf.file.open('rb')
        except (FileNotFoundError, OSError):
            raise Http404('Fayl topilmadi.')

        mime_type, _ = mimetypes.guess_type(pf.original_filename or pf.file.name)
        mime_type = mime_type or 'application/octet-stream'

        response = FileResponse(file_handle, content_type=mime_type)
        safe_name = (pf.original_filename or Path(pf.file.name).name).replace('"', '')
        response['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Content-Security-Policy'] = "default-src 'none'"
        return response


class FileDeleteView(RoleRequiredMixin, View):
    """Fayl o'chirish — faqat yuklagan yoki ADMIN/DIRECTOR."""
    allowed_roles = ('ADMIN', 'DIRECTOR', 'MANAGER')

    def post(self, request, uid):
        from apps.core.models import ProjectFile
        pf = get_object_or_404(ProjectFile, uid=uid)

        role = getattr(request.user, 'role', '')
        can_delete = (
            role in ('ADMIN', 'DIRECTOR')
            or request.user.is_superuser
            or pf.uploaded_by == request.user
        )
        if not can_delete:
            messages.error(request, 'Bu faylni o`chirish uchun ruxsat yo`q.')
            return redirect('core:file-list')

        title = pf.title
        try:
            pf.file.delete(save=False)   # diskdan o'chirish
        except Exception:
            pass
        pf.delete()
        messages.success(request, f'"{title}" o`chirildi.')
        return redirect('core:file-list')
