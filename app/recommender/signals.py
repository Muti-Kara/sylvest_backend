from django.db.models.signals import post_save
from django.dispatch import receiver

from api.tasks import reward_and_notify
from recommender.models import *
from recommender.recommend import Recommender
from chat.models import Room

recommender = Recommender()


@receiver(post_save, sender=Follow)
def on_follow(sender, instance: Follow, created, **kwargs):
    if instance.follow_status == Follow.Status.FOLLOWING:
        recommender.add_relation(
            "u2u", instance.follower.id, instance.followee.id)
    else:
        recommender.remove_relation(
            "u2u", instance.follower.id, instance.followee.id)


@receiver(post_save, sender=UserPostRelation)
def on_like(sender, instance: UserPostRelation, created, **kwargs):
    if created:
        reward_and_notify(instance.post.author, instance.user,
                          "like", instance.post.id)

    if instance.is_liked:
        recommender.add_relation("u2p", instance.user.id, instance.post.id)
    else:
        recommender.remove_relation("u2p", instance.user.id, instance.post.id)


@receiver(post_save, sender=RoledUser)
def on_join(sender, instance: RoledUser, created, **kwargs):
    if created:
        room = Room.objects.get(community=instance.community)
        room.participants.add(instance.user)
        if instance.privilege == RoledUser.Roles.admin:
            room.admins.add(instance.user)
        reward_and_notify(
            instance.community.get_founder(),
            instance.user, "join", instance.community.id)
    else:
        if instance.privilege == RoledUser.Roles.not_member \
                or instance.privilege == RoledUser.Roles.none or instance.is_banned:
            room = Room.objects.get(community=instance.community)
            room.participants.remove(instance.user)
            room.admins.remove(instance.user)
            if RoledUser.objects.exclude(privilege=0)\
                    .filter(community=instance.community).count() == 0:
                instance.community.delete()
                room.delete()


@receiver(post_save, sender=CommentLike)
def on_comment_like(sender, instance: CommentLike, created, **kwargs):
    if created:
        reward_and_notify(
            instance.comment.author, instance.user,
            "like_comment", instance.comment.post.id)


@receiver(post_save, sender=FundableContribute)
def on_contribute(sender, instance: FundableContribute, created, **kwargs):
    if created:
        reward_and_notify(
            instance.fundable.author, instance.user,
            "contribute", instance.fundable.id)


@receiver(post_save, sender=EventAttend)
def on_attend(sender, instance: EventAttend, created, **kwargs):
    if created:
        reward_and_notify(
            instance.event.author, instance.user,
            "attend", instance.event.id)


@receiver(post_save, sender=PostComment)
def on_comment(sender, instance: PostComment, created, **kwargs):
    if created:
        reward_and_notify(
            instance.post.author, instance.user,
            "comment", instance.post.id)
