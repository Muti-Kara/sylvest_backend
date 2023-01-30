from django.db.models.signals import post_save
from django.dispatch import receiver

from subjects.models import Community
from chat.models import Room


@receiver(post_save, sender=Community)
def on_community_saved(sender, instance: Community, created, **kwargs):
    if created:
        Room.objects.create(
            title=instance.title,
            type=Room.Type.GROUP,
            image=instance.image,
            community=instance
        )

