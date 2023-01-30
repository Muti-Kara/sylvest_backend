from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from api.tasks import send_new_post_notification

from blog.models import MasterPost, Comment
from recommender.models import PostComment
from recommender.recommend import Recommender

recommender = Recommender()


@receiver(post_save, sender=MasterPost)
def send_to_recommender(sender, instance: MasterPost, created, **kwargs):
    if created:
        recommender.add_post_relation(instance)
        for follower in instance.author.profile.get_followers():
            send_new_post_notification(follower.follower, instance.author, instance.id, instance.title)


@receiver(pre_delete, sender=MasterPost)
def delete_from_recommender(sender, instance, **kwargs):
    recommender.remove_post_relation(instance)


@receiver(post_save, sender=Comment)
def on_comment_creation(sender, instance: Comment, created: bool, **kwargs):
    if created:
        post_comment_exists: bool = PostComment.objects.filter(
            post=instance.post, user=instance.author).exists()
        if not post_comment_exists:
            PostComment.objects.create(
                user=instance.author, post=instance.post, comment=instance)
