from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Message, Room, Streak
from api.tasks import send_text_notification
from .tasks import send_message_to_layer_celery, message_action_to_layer_celery


@receiver(pre_save, sender=Message)
def on_message_pre_save(sender, instance: Message, *args, **kwargs) -> None:
    if instance.id is None:
        return
    if instance.seen_by.all().count() == instance.room.participants.all().count():
        instance.seen = True
        message_action_to_layer_celery(instance, 'seen')
    if instance.saved:
        message_action_to_layer_celery(instance, 'saved')


@receiver(post_save, sender=Message)
def on_message_saved(sender, instance: Message, created: bool, **kwargs) -> None:
    if created:
        for user in instance.room.participants.all():
            if user == instance.author:
                continue
            send_text_notification(
                to=user,
                sender=instance.author,
                message_data=instance.content,
                message_type=instance.type
            )
        instance.seen_by.add(instance.author)
        send_message_to_layer_celery(instance)


@receiver(post_save, sender=Room)
def on_room_created(sender, instance: Room, created: bool, **kwargs) -> None:
    if created:
        Streak.objects.create(room=instance)