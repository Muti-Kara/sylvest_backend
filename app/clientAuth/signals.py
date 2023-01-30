from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from django.dispatch import receiver

from subjects.models import Profile
from chain.models import ChainPage
from .models import UnapprovedUser
from .email_handler import EmailHandler


@receiver(post_save, sender=User)
def create_user(sender, instance: User, created, **kwargs):
    if created:
        token = EmailHandler().send_verification_mail(user=instance)
        instance.is_active = False
        instance.save()
        UnapprovedUser.objects.create(user=instance, url_token=token)


@receiver(pre_delete, sender=UnapprovedUser)
def delete_unapproved(sender, instance: UnapprovedUser, **kwargs):
    try:
        user: User = instance.user
        if User.objects.all().contains(user):
            Profile.objects.create(user=user)
            ChainPage.objects.create(user=user)
    except Exception as e:
        print(e)