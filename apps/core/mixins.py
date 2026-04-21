from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class PageMetadataMixin:
    page_title = 'Boshqaruv paneli'
    page_subtitle = 'Asosiy boshqaruv sahifasi'
    breadcrumbs: list[dict[str, str]] = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('page_title', self.page_title)
        context.setdefault('page_subtitle', self.page_subtitle)
        context.setdefault('breadcrumbs', self.breadcrumbs)
        return context


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles: tuple[str, ...] = ()

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.role in self.allowed_roles


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('ADMIN',)


class DirectorRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('ADMIN', 'DIRECTOR')
