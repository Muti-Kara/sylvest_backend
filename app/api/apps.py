from django.apps import AppConfig
from django.db.models.signals import post_migrate

from signals import on_app_start


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        post_migrate.connect(on_app_start, sender=self)
