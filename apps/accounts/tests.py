import os

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import ManagerAccount

from .models import TelegramLoginSession
from .services import TokenService
from .telegram_bot import TelegramBotFlowService


User = get_user_model()


class FakeTelegramBotClient:
    def __init__(self):
        self.messages = []
        self.commands = []

    def send_message(self, **kwargs):
        self.messages.append(kwargs)
        return kwargs

    def set_my_commands(self, commands):
        self.commands = commands
        return commands


class UserModelTest(TestCase):
    def setUp(self):
        os.environ['APP_BASE_URL'] = 'http://testserver'

    def test_role_defaults_to_manager(self):
        user = User.objects.create_user(
            username='manager',
            password='test12345',
            full_name='Manager User',
        )
        self.assertEqual(user.role, User.Role.MANAGER)

    def test_access_token_is_single_use(self):
        user = User.objects.create_user(
            username='telegram-user',
            password='test12345',
            full_name='Telegram User',
            telegram_id=123456789,
        )
        token = TokenService.create_access_token(user)
        consumed_user = TokenService.consume_token(token.token)
        self.assertEqual(consumed_user, user)
        self.assertTrue(token.__class__.objects.get(pk=token.pk).is_used)

    def test_manager_user_gets_manager_account(self):
        user = User.objects.create_user(
            username='wallet-manager',
            password='test12345',
            full_name='Wallet Manager',
            role=User.Role.MANAGER,
            telegram_id=987654321,
        )
        self.assertTrue(ManagerAccount.objects.filter(user=user).exists())

    def test_start_requests_contact_for_unlinked_user(self):
        client = FakeTelegramBotClient()
        TelegramBotFlowService.process_update(
            {
                'update_id': 1,
                'message': {
                    'message_id': 11,
                    'chat': {'id': 5001, 'type': 'private'},
                    'from': {'id': 5001, 'username': 'new_manager'},
                    'text': '/start',
                },
            },
            client=client,
        )

        session = TelegramLoginSession.objects.get(telegram_id=5001)
        self.assertEqual(session.state, TelegramLoginSession.State.WAITING_CONTACT)
        self.assertEqual(client.messages[0]['reply_markup']['keyboard'][0][0]['request_contact'], True)

    def test_contact_links_user_and_sends_access_link(self):
        user = User.objects.create_user(
            username='linked-user',
            password='test12345',
            full_name='Linked User',
            role=User.Role.DIRECTOR,
            phone='+998901234567',
        )
        client = FakeTelegramBotClient()

        TelegramBotFlowService.process_update(
            {
                'update_id': 2,
                'message': {
                    'message_id': 12,
                    'chat': {'id': 7001, 'type': 'private'},
                    'from': {'id': 7001, 'username': 'linked_user_bot'},
                    'contact': {
                        'user_id': 7001,
                        'phone_number': '998901234567',
                    },
                },
            },
            client=client,
        )

        user.refresh_from_db()
        session = TelegramLoginSession.objects.get(telegram_id=7001)

        self.assertEqual(user.telegram_id, 7001)
        self.assertEqual(session.user, user)
        self.assertEqual(session.state, TelegramLoginSession.State.ACCESS_SENT)
        self.assertIn('/accounts/access/', client.messages[-1]['reply_markup']['inline_keyboard'][0][0]['url'])

    def test_token_command_for_linked_user_sends_new_access_link(self):
        user = User.objects.create_user(
            username='token-user',
            password='test12345',
            full_name='Token User',
            role=User.Role.MANAGER,
            phone='+998909999999',
            telegram_id=9001,
        )
        client = FakeTelegramBotClient()

        TelegramBotFlowService.process_update(
            {
                'update_id': 3,
                'message': {
                    'message_id': 13,
                    'chat': {'id': 9001, 'type': 'private'},
                    'from': {'id': 9001, 'username': 'token_user'},
                    'text': '/token',
                },
            },
            client=client,
        )

        self.assertEqual(client.messages[-1]['reply_markup']['inline_keyboard'][0][0]['text'], 'Saytga kirish')
        self.assertTrue(user.access_tokens.exists())
