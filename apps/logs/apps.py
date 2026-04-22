from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.logs'
    verbose_name = 'Audit va xavfsizlik loglari'

    def ready(self):
        from . import signals  # noqa: F401
