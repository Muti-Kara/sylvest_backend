import asyncio
from celery import shared_task
from django.contrib.auth.models import User

from api.models import Notification
from .models import Message, Room
from .manager import send_message_to_layer, message_action_to_layer
from .serializers import MessageSerializer


@shared_task
def update_notifications(user: User) -> None:
    for notification in Notification.objects.filter(user=user, show_on_profile=False):
        notification.read = True
        notification.save()


@shared_task
def send_message_to_layer_celery(message: Message) -> None:
    participants: list[str] = [
        participant.username
        for participant in message.room.participants.all()
    ]
    message_data = MessageSerializer(message).data
    asyncio.run(send_message_to_layer(participants, message_data))


@shared_task
def message_action_to_layer_celery(message: Message, action: str = 'seen') -> None:
    participants: list[str] = [
        participant.username
        for participant in message.room.participants.all()
    ]
    message_id, room_id = message.id, message.room.id
    asyncio.run(message_action_to_layer(participants, message_id, room_id, action))
