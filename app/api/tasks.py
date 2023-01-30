from decimal import Decimal
from celery import shared_task

from api.notifications import *
from api.models import *


@shared_task
def send_text_notification(to: User, sender: User, message_data: str, message_type: str) -> None:
    text_notification(to, sender, message_data, message_type)


@shared_task
def send_level_up_notification(to: User) -> None:
    level_up_notification(to)


@shared_task
def send_token_notification(to: User, action: str, sender: User = None, amount: Decimal = None) -> None:
    token_notification(to=to, action=action, sender=sender, amount=amount)


@shared_task
def send_new_post_notification(to: User, sender: User, post_id: int, post_title: str) -> None:
    new_post_notification(to, sender, post_id, post_title)


@shared_task
def reward_and_notify(owner: User, user: User, action: str, item_id: int):
    if owner == user:
        return
    owner.chainpage.get_reward(action)
    engage_notification(owner, user, action, item_id)
