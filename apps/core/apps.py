from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self):
        from django.db.backends.signals import connection_created

        def _sqlite_pragmas(sender, connection, **kwargs):
            """
            SQLite uchun WAL rejimi va tezlashtiruvchi sozlamalar.
            WAL: bir vaqtda o'qish va yozish (Telegram bot + web bir-birini bloklamas).
            """
            if connection.vendor != 'sqlite':
                return
            with connection.cursor() as cur:
                cur.execute('PRAGMA journal_mode=WAL;')
                cur.execute('PRAGMA synchronous=NORMAL;')   # fsync'ni kamaytiradi
                cur.execute('PRAGMA cache_size=-32000;')    # 32 MB sahifa keshi
                cur.execute('PRAGMA temp_store=MEMORY;')    # vaqtli jadvallar xotirada
                cur.execute('PRAGMA mmap_size=134217728;')  # 128 MB mmap

        connection_created.connect(_sqlite_pragmas)
