from django.urls import path

from .views import AccessTokenLoginView, TelegramBotWebhookView, TelegramEntryView, TelegramMiniAppVerifyView, UserLogoutView

app_name = 'accounts'

urlpatterns = [
    path('telegram/', TelegramEntryView.as_view(), name='telegram-entry'),
    path('telegram/webhook/', TelegramBotWebhookView.as_view(), name='telegram-webhook'),
    path('access/<str:token>/', AccessTokenLoginView.as_view(), name='access-token'),
    path('telegram/verify/', TelegramMiniAppVerifyView.as_view(), name='telegram-verify'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
]
