from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.finance.models import CurrencyChoices
from apps.finance.services import CompanyBalanceService, ExchangeRateService, ManagerBalanceService
from apps.logs.services import AuditLogService
from config.settings.env import env

from .models import TelegramBotState, TelegramLoginSession, User
from .services import TelegramAuthService, TokenService


class TelegramBotConfigService:
    @staticmethod
    def bot_token():
        token = env('TELEGRAM_BOT_TOKEN', '')
        if not token:
            raise ValidationError('TELEGRAM_BOT_TOKEN sozlanmagan.')
        return token

    @staticmethod
    def base_url():
        return (env('APP_BASE_URL', 'http://127.0.0.1:8000') or 'http://127.0.0.1:8000').rstrip('/')

    @classmethod
    def webapp_url(cls):
        value = (env('TELEGRAM_WEBAPP_URL', '') or '').strip().rstrip('/')
        if value.startswith('https://'):
            return value
        return ''

    @staticmethod
    def webhook_secret():
        return env('TELEGRAM_WEBHOOK_SECRET', '') or ''


class TelegramLoginSessionService:
    @staticmethod
    def upsert_session(*, telegram_id, chat_id=None, username='', phone='', user=None, state=TelegramLoginSession.State.NEW, last_error=''):
        session, _ = TelegramLoginSession.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                'chat_id': chat_id,
                'telegram_username': username or '',
                'phone': phone or '',
                'user': user,
                'state': state,
                'last_error': last_error,
                'last_interaction_at': timezone.now(),
            },
        )
        return session

    @classmethod
    def mark_waiting_contact(cls, *, telegram_id, chat_id=None, username=''):
        return cls.upsert_session(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            state=TelegramLoginSession.State.WAITING_CONTACT,
            last_error='',
        )

    @classmethod
    def mark_waiting_username(cls, *, telegram_id, chat_id=None, username='', phone='', user=None, last_error=''):
        return cls.upsert_session(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            phone=phone,
            user=user,
            state=TelegramLoginSession.State.WAITING_USERNAME,
            last_error=last_error,
        )

    @classmethod
    def mark_waiting_password(cls, *, telegram_id, chat_id=None, username='', phone='', user=None, last_error=''):
        return cls.upsert_session(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            phone=phone,
            user=user,
            state=TelegramLoginSession.State.WAITING_PASSWORD,
            last_error=last_error,
        )

    @classmethod
    def mark_linked(cls, *, telegram_id, chat_id=None, username='', phone='', user=None):
        return cls.upsert_session(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            phone=phone,
            user=user,
            state=TelegramLoginSession.State.LINKED,
            last_error='',
        )

    @classmethod
    def mark_access_sent(cls, *, telegram_id, chat_id=None, username='', phone='', user=None):
        return cls.upsert_session(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            phone=phone,
            user=user,
            state=TelegramLoginSession.State.ACCESS_SENT,
            last_error='',
        )

    @classmethod
    def mark_error(cls, *, telegram_id, chat_id=None, username='', phone='', error_message=''):
        return cls.upsert_session(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            phone=phone,
            state=TelegramLoginSession.State.ERROR,
            last_error=error_message,
        )

    @classmethod
    def mark_blocked(cls, *, telegram_id, chat_id=None, username='', phone='', error_message=''):
        return cls.upsert_session(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            phone=phone,
            state=TelegramLoginSession.State.BLOCKED,
            last_error=error_message,
        )


class TelegramUserLinkService:
    @staticmethod
    def normalize_phone(phone: str) -> str:
        return ''.join(symbol for symbol in str(phone or '') if symbol.isdigit())

    @classmethod
    def phone_candidates(cls, phone: str) -> list[str]:
        original = str(phone or '').strip()
        digits = cls.normalize_phone(phone)
        candidates = {original, digits}

        if digits:
            candidates.add(f'+{digits}')
        if len(digits) == 9:
            candidates.add(f'998{digits}')
            candidates.add(f'+998{digits}')
        if digits.startswith('998') and len(digits) > 3:
            local = digits[3:]
            candidates.add(local)
            candidates.add(f'+{digits}')
            candidates.add(f'+998{local}')

        return [value for value in candidates if value]

    @classmethod
    def find_user_by_phone(cls, phone: str) -> User:
        candidates = cls.phone_candidates(phone)
        matches = list(User.objects.filter(phone__in=candidates)[:2])
        if not matches:
            raise ValidationError('Bu telefon raqam bazada topilmadi.')
        if len(matches) > 1:
            raise ValidationError('Bu telefon raqam bir nechta foydalanuvchiga bog`langan.')
        user = matches[0]
        if not user.is_active:
            raise ValidationError('Bu foydalanuvchi faol emas.')
        return user

    @classmethod
    def link_user(cls, *, telegram_id, telegram_username='', phone='') -> User:
        user = cls.find_user_by_phone(phone)
        conflicting_user = User.objects.filter(telegram_id=telegram_id).exclude(pk=user.pk).first()
        if conflicting_user:
            raise ValidationError('Bu Telegram akkaunti boshqa foydalanuvchiga biriktirilgan.')
        if user.telegram_id and user.telegram_id != telegram_id:
            raise ValidationError('Bu foydalanuvchi boshqa Telegram akkauntiga allaqachon bog`langan.')

        changed_fields = []
        if user.telegram_id != telegram_id:
            user.telegram_id = telegram_id
            changed_fields.append('telegram_id')
        if telegram_username and user.telegram_username != telegram_username:
            user.telegram_username = telegram_username
            changed_fields.append('telegram_username')
        if not user.phone and phone:
            user.phone = phone
            changed_fields.append('phone')

        if changed_fields:
            user.save(update_fields=changed_fields)
        return user


class TelegramBotStateService:
    @staticmethod
    def get_state(name='default'):
        state, _ = TelegramBotState.objects.get_or_create(name=name)
        return state

    @classmethod
    def current_offset(cls, name='default'):
        return cls.get_state(name=name).last_update_id

    @classmethod
    def store_offset(cls, last_update_id, name='default'):
        state = cls.get_state(name=name)
        if last_update_id > state.last_update_id:
            state.last_update_id = last_update_id
            state.save(update_fields=['last_update_id', 'updated_at'])
        return state.last_update_id


class TelegramBotApiClient:
    def __init__(self, token: str | None = None):
        self.token = token or TelegramBotConfigService.bot_token()

    def _request(self, method: str, payload: dict | None = None, timeout: int = 30):
        endpoint = f'https://api.telegram.org/bot{self.token}/{method}'
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = Request(
            endpoint,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST' if data is not None else 'GET',
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                response_payload = json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            body = exc.read().decode('utf-8', errors='ignore')
            raise ValidationError(f'Telegram API xatosi: {exc.code} {body}') from exc
        except URLError as exc:
            raise ValidationError('Telegram API bilan aloqa qilib bo`lmadi.') from exc

        if not response_payload.get('ok'):
            raise ValidationError(response_payload.get('description') or 'Telegram API xatosi.')
        return response_payload.get('result')

    def get_updates(self, *, offset=None, timeout=25):
        payload = {
            'timeout': timeout,
            'allowed_updates': ['message'],
        }
        if offset is not None:
            payload['offset'] = offset
        return self._request('getUpdates', payload, timeout=timeout + 10)

    def send_message(self, *, chat_id, text, reply_markup=None):
        payload = {
            'chat_id': chat_id,
            'text': text,
        }
        if reply_markup is not None:
            payload['reply_markup'] = reply_markup
        return self._request('sendMessage', payload)

    def set_my_commands(self, commands: list[dict]):
        return self._request('setMyCommands', {'commands': commands})


class TelegramBotFlowService:
    @staticmethod
    def _extract_error_message(error) -> str:
        if hasattr(error, 'messages') and error.messages:
            return error.messages[0]
        return str(error)

    @staticmethod
    def _contact_keyboard():
        return {
            'keyboard': [[{'text': 'Telefon raqamni yuborish', 'request_contact': True}]],
            'resize_keyboard': True,
            'one_time_keyboard': True,
        }

    @staticmethod
    def _remove_keyboard():
        return {'remove_keyboard': True}

    @staticmethod
    def _main_keyboard():
        return {
            'keyboard': [
                [{'text': '🔗 Saytga kirish'}],
                [{'text': '💱 Bugungi kurs'}, {'text': '💰 Ferma hisobi'}],
                [{'text': '📱 Mini App'}, {'text': 'ℹ️ Yordam'}],
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False,
        }

    @classmethod
    def _access_url(cls, token: str):
        path = reverse('accounts:access-token', kwargs={'token': token})
        return f'{TelegramBotConfigService.base_url()}{path}'

    @classmethod
    def _menu_markup(cls, access_url: str):
        inline_keyboard = [[{'text': 'Saytga kirish', 'url': access_url}]]
        webapp_url = TelegramBotConfigService.webapp_url()
        if webapp_url:
            inline_keyboard.append([{'text': 'Mini App ochish', 'web_app': {'url': webapp_url}}])
        return {'inline_keyboard': inline_keyboard}

    @classmethod
    def sync_commands(cls, client: TelegramBotApiClient):
        client.set_my_commands(
            [
                {'command': 'start', 'description': 'Tizimga kirish'},
                {'command': 'token', 'description': 'Yangi access link olish'},
                {'command': 'help', 'description': 'Yordam'},
            ]
        )

    @staticmethod
    def _actor(message: dict):
        actor = message.get('from', {})
        chat = message.get('chat', {})
        return {
            'telegram_id': actor.get('id'),
            'chat_id': chat.get('id') or actor.get('id'),
            'username': actor.get('username', ''),
        }

    @classmethod
    def _send_contact_request(cls, *, client, chat_id, telegram_id, username):
        TelegramLoginSessionService.mark_waiting_contact(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
        )
        client.send_message(
            chat_id=chat_id,
            text='Assalomu alaykum. Tizimga kirish uchun telefon raqamingizni Telegram contact sifatida yuboring.',
            reply_markup=cls._contact_keyboard(),
        )

    @classmethod
    def _send_access_menu(cls, *, client, user, chat_id, telegram_id, username, phone=''):
        access_token = TokenService.create_access_token(user)
        access_url = cls._access_url(access_token.token)
        TelegramLoginSessionService.mark_access_sent(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            phone=phone,
            user=user,
        )
        client.send_message(
            chat_id=chat_id,
            text=(
                f'{user.full_name}, kirish havolasi tayyor.\n'
                'Havola bir martalik va qisqa muddat amal qiladi.\n'
                'Yangi link kerak bo`lsa /token yuboring.'
            ),
            reply_markup=cls._menu_markup(access_url),
        )
        client.send_message(
            chat_id=chat_id,
            text='Menyu tayyor. Quyidagi tugmalardan foydalanishingiz mumkin.',
            reply_markup=cls._main_keyboard(),
        )
        AuditLogService.log(
            user=user,
            action='telegram_bot_access_sent',
            model_name='User',
            object_id=str(user.pk),
            description=f'{user} uchun Telegram bot orqali access link yuborildi.',
        )

    @classmethod
    def _send_help(cls, *, client, chat_id):
        client.send_message(
            chat_id=chat_id,
            text=(
                'Kirish uchun /start yuboring.\n'
                'Avval telefon raqam, keyin username va parol tekshiriladi.\n'
                'Menyu tugmalari: Saytga kirish, Bugungi kurs, Ferma hisobi.'
            ),
            reply_markup=cls._main_keyboard(),
        )

    @staticmethod
    def _money(value):
        return f'{value:,.2f}'.replace(',', ' ')

    @staticmethod
    def _format_datetime(value):
        if not value:
            return '-'
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        return timezone.localtime(value).strftime('%Y-%m-%d %H:%M')

    @classmethod
    def _send_rate(cls, *, client, chat_id):
        rate = ExchangeRateService.latest_rate()
        if not rate:
            client.send_message(
                chat_id=chat_id,
                text='USD kursi hali kiritilmagan. Admin paneldan yoki moliya bo`limidan kursni yangilang.',
                reply_markup=cls._main_keyboard(),
            )
            return
        client.send_message(
            chat_id=chat_id,
            text=(
                'Bugungi USD kursi:\n'
                f'1 USD = {cls._money(rate.usd_to_uzs)} UZS\n'
                f'Yangilangan vaqt: {cls._format_datetime(rate.effective_at)}'
            ),
            reply_markup=cls._main_keyboard(),
        )

    @classmethod
    def _send_balance(cls, *, client, chat_id, user):
        if getattr(user, 'role', '') == User.Role.MANAGER:
            try:
                balances = ManagerBalanceService.summary_for_account(user.manager_account)
                title = 'Mening hisobim'
            except Exception:
                balances = {CurrencyChoices.UZS: 0, CurrencyChoices.USD: 0}
                title = 'Mening hisobim'
        else:
            balances = CompanyBalanceService.summary()
            title = 'Ferma hisobi'
        client.send_message(
            chat_id=chat_id,
            text=(
                f'{title}:\n'
                f'UZS: {cls._money(balances[CurrencyChoices.UZS])}\n'
                f'USD: {cls._money(balances[CurrencyChoices.USD])}'
            ),
            reply_markup=cls._main_keyboard(),
        )

    @classmethod
    def handle_start(cls, message: dict, client: TelegramBotApiClient):
        actor = cls._actor(message)
        telegram_id = actor['telegram_id']
        if not telegram_id:
            return

        try:
            user = TelegramAuthService.get_active_user_by_telegram_id(telegram_id)
        except ValidationError:
            cls._send_contact_request(
                client=client,
                chat_id=actor['chat_id'],
                telegram_id=telegram_id,
                username=actor['username'],
            )
            return

        TelegramLoginSessionService.mark_waiting_password(
            telegram_id=telegram_id,
            chat_id=actor['chat_id'],
            username=actor['username'],
            phone=user.phone,
            user=user,
        )
        client.send_message(
            chat_id=actor['chat_id'],
            text=f'{user.full_name}, akkaunt topildi. Xavfsizlik uchun parolingizni yuboring.',
            reply_markup=cls._remove_keyboard(),
        )

    @classmethod
    def handle_contact(cls, message: dict, client: TelegramBotApiClient):
        actor = cls._actor(message)
        contact = message.get('contact') or {}
        telegram_id = actor['telegram_id']
        if not telegram_id:
            return

        if contact.get('user_id') and contact.get('user_id') != telegram_id:
            error_message = 'Faqat o`zingizning telefon raqamingizni yuborishingiz mumkin.'
            TelegramLoginSessionService.mark_error(
                telegram_id=telegram_id,
                chat_id=actor['chat_id'],
                username=actor['username'],
                phone=contact.get('phone_number', ''),
                error_message=error_message,
            )
            client.send_message(
                chat_id=actor['chat_id'],
                text=error_message,
                reply_markup=cls._contact_keyboard(),
            )
            return

        phone = contact.get('phone_number', '')
        try:
            user = TelegramUserLinkService.find_user_by_phone(phone)
        except ValidationError as error:
            error_message = cls._extract_error_message(error)
            TelegramLoginSessionService.mark_error(
                telegram_id=telegram_id,
                chat_id=actor['chat_id'],
                username=actor['username'],
                phone=phone,
                error_message=error_message,
            )
            client.send_message(
                chat_id=actor['chat_id'],
                text=error_message,
                reply_markup=cls._contact_keyboard(),
            )
            return

        TelegramLoginSessionService.mark_waiting_username(
            telegram_id=telegram_id,
            chat_id=actor['chat_id'],
            username=actor['username'],
            phone=phone,
            user=user,
        )
        client.send_message(
            chat_id=actor['chat_id'],
            text='Telefon raqam topildi. Endi Django username kiriting.',
            reply_markup=cls._remove_keyboard(),
        )

    @classmethod
    def _complete_password_login(cls, *, message, client, session, password):
        actor = cls._actor(message)
        user = session.user
        if not user or not user.is_active:
            client.send_message(chat_id=actor['chat_id'], text='Foydalanuvchi topilmadi yoki faol emas.')
            return
        if not user.check_password(password):
            TelegramLoginSessionService.mark_waiting_password(
                telegram_id=actor['telegram_id'],
                chat_id=actor['chat_id'],
                username=actor['username'],
                phone=session.phone,
                user=user,
                last_error='Parol noto`g`ri.',
            )
            client.send_message(
                chat_id=actor['chat_id'],
                text='Parol noto`g`ri. Qaytadan parol yuboring yoki /start bilan boshidan boshlang.',
                reply_markup=cls._remove_keyboard(),
            )
            return

        conflicting_user = User.objects.filter(telegram_id=actor['telegram_id']).exclude(pk=user.pk).first()
        if conflicting_user:
            client.send_message(chat_id=actor['chat_id'], text='Bu Telegram akkaunti boshqa foydalanuvchiga bog`langan.')
            return
        if user.telegram_id and user.telegram_id != actor['telegram_id']:
            client.send_message(chat_id=actor['chat_id'], text='Bu foydalanuvchi boshqa Telegram akkauntiga allaqachon bog`langan.')
            return

        changed_fields = []
        if user.telegram_id != actor['telegram_id']:
            user.telegram_id = actor['telegram_id']
            changed_fields.append('telegram_id')
        if actor['username'] and user.telegram_username != actor['username']:
            user.telegram_username = actor['username']
            changed_fields.append('telegram_username')
        if session.phone and not user.phone:
            user.phone = session.phone
            changed_fields.append('phone')
        if changed_fields:
            user.save(update_fields=changed_fields)

        TelegramLoginSessionService.mark_linked(
            telegram_id=actor['telegram_id'],
            chat_id=actor['chat_id'],
            username=actor['username'],
            phone=session.phone or user.phone,
            user=user,
        )
        client.send_message(
            chat_id=actor['chat_id'],
            text='Akkaunt tasdiqlandi. Endi kirish havolasini yuboraman.',
            reply_markup=cls._main_keyboard(),
        )
        cls._send_access_menu(
            client=client,
            user=user,
            chat_id=actor['chat_id'],
            telegram_id=actor['telegram_id'],
            username=actor['username'],
            phone=session.phone or user.phone,
        )
        AuditLogService.log(
            user=user,
            action='telegram_bot_user_linked',
            model_name='User',
            object_id=str(user.pk),
            description=f'{user} Telegram bot orqali username/parol bilan tasdiqlandi.',
        )

    @classmethod
    def handle_text(cls, message: dict, client: TelegramBotApiClient):
        actor = cls._actor(message)
        telegram_id = actor['telegram_id']
        if not telegram_id:
            return

        text = (message.get('text') or '').strip().lower()
        if text in {'/help', 'help'}:
            cls._send_help(client=client, chat_id=actor['chat_id'])
            return

        session = TelegramLoginSession.objects.filter(telegram_id=telegram_id).select_related('user').first()
        if session and session.state == TelegramLoginSession.State.WAITING_USERNAME:
            raw_text = (message.get('text') or '').strip()
            if not session.user:
                cls._send_contact_request(
                    client=client,
                    chat_id=actor['chat_id'],
                    telegram_id=telegram_id,
                    username=actor['username'],
                )
                return
            if raw_text != session.user.username:
                TelegramLoginSessionService.mark_waiting_username(
                    telegram_id=telegram_id,
                    chat_id=actor['chat_id'],
                    username=actor['username'],
                    phone=session.phone,
                    user=session.user,
                    last_error='Username noto`g`ri.',
                )
                client.send_message(
                    chat_id=actor['chat_id'],
                    text='Username noto`g`ri. Django admin paneldagi username bilan bir xil kiriting.',
                    reply_markup=cls._remove_keyboard(),
                )
                return
            TelegramLoginSessionService.mark_waiting_password(
                telegram_id=telegram_id,
                chat_id=actor['chat_id'],
                username=actor['username'],
                phone=session.phone,
                user=session.user,
            )
            client.send_message(
                chat_id=actor['chat_id'],
                text='Username tasdiqlandi. Endi parolingizni yuboring.',
                reply_markup=cls._remove_keyboard(),
            )
            return

        if session and session.state == TelegramLoginSession.State.WAITING_PASSWORD:
            cls._complete_password_login(
                message=message,
                client=client,
                session=session,
                password=(message.get('text') or '').strip(),
            )
            return

        if text in {'💱 bugungi kurs', 'bugungi kurs', 'kurs', '/kurs'}:
            cls._send_rate(client=client, chat_id=actor['chat_id'])
            return

        if text in {'💰 ferma hisobi', 'ferma hisobi', 'hisob', 'balans', '/balance'}:
            try:
                user = TelegramAuthService.get_active_user_by_telegram_id(telegram_id)
            except ValidationError:
                cls._send_contact_request(
                    client=client,
                    chat_id=actor['chat_id'],
                    telegram_id=telegram_id,
                    username=actor['username'],
                )
                return
            cls._send_balance(client=client, chat_id=actor['chat_id'], user=user)
            return

        if text in {'📱 mini app', 'mini app'}:
            webapp_url = TelegramBotConfigService.webapp_url()
            if webapp_url:
                client.send_message(
                    chat_id=actor['chat_id'],
                    text='Mini App tugmasi:',
                    reply_markup={'inline_keyboard': [[{'text': 'Mini App ochish', 'web_app': {'url': webapp_url}}]]},
                )
                return
            client.send_message(
                chat_id=actor['chat_id'],
                text='Mini App uchun HTTPS TELEGRAM_WEBAPP_URL kerak. Localhost Telegram ichida Web App sifatida ochilmaydi.',
                reply_markup=cls._main_keyboard(),
            )
            return

        if text in {'/token', 'token', 'link', 'saytga kirish', '🔗 saytga kirish'}:
            try:
                user = TelegramAuthService.get_active_user_by_telegram_id(telegram_id)
            except ValidationError:
                cls._send_contact_request(
                    client=client,
                    chat_id=actor['chat_id'],
                    telegram_id=telegram_id,
                    username=actor['username'],
                )
                return

            cls._send_access_menu(
                client=client,
                user=user,
                chat_id=actor['chat_id'],
                telegram_id=telegram_id,
                username=actor['username'],
                phone=user.phone,
            )
            return

        cls._send_help(client=client, chat_id=actor['chat_id'])

    @classmethod
    def process_update(cls, update: dict, client: TelegramBotApiClient | None = None):
        client = client or TelegramBotApiClient()
        message = update.get('message')
        if not message:
            return

        if message.get('contact'):
            cls.handle_contact(message, client)
            return

        text = (message.get('text') or '').strip()
        if text.startswith('/start'):
            cls.handle_start(message, client)
            return

        cls.handle_text(message, client)
