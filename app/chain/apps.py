from django.apps import AppConfig


class ChainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chain'

    def ready(self):
        import chain.signals
