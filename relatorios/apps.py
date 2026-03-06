from django.apps import AppConfig


class RelatoriosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'relatorios'
    verbose_name = 'Relatórios de Vendas'

    def ready(self):
        try:
            from django.db import connection
            if connection.vendor == 'sqlite':
                with connection.cursor() as c:
                    c.execute('PRAGMA journal_mode=WAL')
                    c.execute('PRAGMA synchronous=NORMAL')
                    c.execute('PRAGMA cache_size=-64000')
                    c.execute('PRAGMA temp_store=MEMORY')
        except Exception:
            pass
