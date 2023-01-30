import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sylvest_django.settings")
celery_app = Celery("sylvest_django")

celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()


@celery_app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


celery_app.conf.beat_schedule = {
    "transfer-scheduler": {
        "task": "create_transfer_log",
        'schedule': 30.0
    },
    "sign-scheduler": {
        "task": "sign_transactions",
        'schedule': 10.0
    }
}
