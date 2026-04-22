import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from config.settings.env import env

from apps.logs.services import AuditLogService

from .services import TelegramAuthService, TokenService
from .telegram_bot import TelegramBotConfigService, TelegramBotFlowService

logger = logging.getLogger(__name__)


class TelegramEntryView(TemplateView):
    template_name = 'accounts/telegram_entry.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Telegram orqali kirish'
        context['page_subtitle'] = 'Login faqat Telegram bot yoki Mini App orqali amalga oshiriladi'
        context['telegram_bot_username'] = env('TELEGRAM_BOT_USERNAME', '')
        context['telegram_webapp_url'] = env('TELEGRAM_WEBAPP_URL', '')
        context['next_url'] = self.request.GET.get('next', reverse('dashboard:index'))
        return context


@method_decorator(never_cache, name='dispatch')
class AccessTokenLoginView(View):
    def get(self, request, token):
        try:
            user = TokenService.consume_token(token)
        except ValidationError as error:
            messages.error(request, error.message)
            return redirect('accounts:telegram-entry')
        login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
        AuditLogService.log_from_request(
            request,
            user=user,
            action='telegram_token_login',
            model_name='User',
            object_id=str(user.pk),
            description=f'{user} bir martalik token orqali tizimga kirdi. Token ID: {getattr(user, "_consumed_access_token_id", "-")}',
        )
        return redirect(request.GET.get('next') or reverse('dashboard:index'))


@method_decorator(csrf_exempt, name='dispatch')
class TelegramMiniAppVerifyView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}') if request.body else {}
        except json.JSONDecodeError:
            payload = {}
        init_data = payload.get('init_data') or request.POST.get('init_data')
        next_url = payload.get('next') or request.POST.get('next') or reverse('dashboard:index')
        try:
            user = TelegramAuthService.authenticate_from_init_data(init_data)
        except ValidationError as error:
            return JsonResponse({'ok': False, 'error': error.message}, status=400)

        login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
        AuditLogService.log_from_request(
            request,
            user=user,
            action='telegram_mini_app_login',
            model_name='User',
            object_id=str(user.pk),
            description=f'{user} Telegram Mini App orqali tizimga kirdi.',
        )
        return JsonResponse({'ok': True, 'redirect_url': next_url})


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:telegram-entry')


@method_decorator(csrf_exempt, name='dispatch')
class TelegramBotWebhookView(View):
    def post(self, request):
        secret = TelegramBotConfigService.webhook_secret()
        if secret and request.headers.get('X-Telegram-Bot-Api-Secret-Token') != secret:
            return HttpResponseForbidden('Forbidden')

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}') if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

        try:
            TelegramBotFlowService.process_update(payload)
        except ValidationError as error:
            logger.warning('Telegram webhook validation error: %s', error)
        except Exception:
            logger.exception('Telegram webhook unexpected error')
        return JsonResponse({'ok': True})
