from django.apps import AppConfig


class ClientauthConfig(AppConfig):
    name = 'clientAuth'

    def ready(self):
        import clientAuth.signals
