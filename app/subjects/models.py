from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet, Q
from django.core.files.base import ContentFile
from api.dynamic_links import DynamicLinkManager

from recommender.models import Follow, RoledUser
from api.models import Notification
from blog.models import MasterPost, Tag
from api.helper import compress_image, process_base64_image


class Subject(models.Model):
    class Meta:
        abstract = True

    title = models.CharField(max_length=100, unique=True)
    info = models.JSONField(null=True, blank=True)
    about = models.TextField(max_length=500, null=True, blank=True)

    image = models.ImageField(
        upload_to="public/subject_pics",
        null=True, blank=True
    )
    banner = models.ImageField(
        upload_to="public/subject_banners",
        null=True, blank=True
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super(Subject, self).save(*args, **kwargs)

        if self.image is not None:
            compress_image(self.image, down_size=True, down_size_width=300)
        if self.banner is not None:
            compress_image(self.banner)


class Profile(Subject):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    interests = models.ManyToManyField(
        Tag, related_name="user_interests", blank=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    region = models.CharField(max_length=50, blank=True)

    gender = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(max_length=500, null=True, blank=True)

    is_private = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.user.username

    def get_interests(self) -> QuerySet[Tag]:
        return self.interests.all()

    def get_followers(self) -> QuerySet[Follow]:
        return Follow.objects.filter(
            followee=self.user,
            follow_status=Follow.Status.FOLLOWING
        )

    def is_follower(self, user: User) -> bool:
        try:
            Follow.objects.get(
                followee=self.user,
                follower=user,
                follow_status=Follow.Status.FOLLOWING
            )
            return True
        except:
            return False

    def get_following(self) -> QuerySet[Follow]:
        return Follow.objects.filter(
            follower=self.user,
            follow_status=Follow.Status.FOLLOWING
        )

    def is_following(self, user: User) -> bool:
        try:
            Follow.objects.get(
                follower=self.user,
                followee=user,
                follow_status=Follow.Status.FOLLOWING
            )
            return True
        except:
            return False

    def get_joined_communities_roles(self) -> QuerySet[RoledUser]:
        return RoledUser.objects.filter(user=self.user)\
            .exclude(privilege=RoledUser.Roles.not_member)

    def __default_recommendation(self, slice_index: int = 30) -> list[User]:
        follows: QuerySet[Follow] = Follow.objects.filter(
            Q(follower=self.user) | Q(followee=self.user),
            follow_status=Follow.Status.FOLLOWING
        )[:slice_index]
        return [
            follow.follower if follow.follower != self.user
            else follow.followee for follow in follows
        ]

    def friend_recommendation(self) -> list[User]:
        from recommender.recommend import Recommender

        try:
            recommendations: QuerySet = Recommender()\
                .get_recommended_users(self.user)
            if not recommendations:
                return self.__default_recommendation()
            # if self.user.id in recommendations:
            #     recommendations.remove(self.user.id)
            result: QuerySet[User] = User.objects.filter(
                id__in=recommendations)
            return list(result)
        except Exception as e:
            print(e.with_traceback)
            return self.__default_recommendation()

    @staticmethod
    def read_notifications(notifications: list[Notification]) -> None:
        for notification in notifications:
            notification.read = True
            notification.save()

    def get_notifications(self) -> QuerySet[Notification]:
        return Notification.objects.filter(
            user=self.user, show_on_profile=True).order_by('-id')

    def is_profile_notifications_unread(self) -> bool:
        notifications: list[Notification] = Notification.objects.filter(
            user=self.user, show_on_profile=True)
        for notification in notifications:
            if not notification.read:
                return True
        return False

    def is_message_notifications_unread(self) -> bool:
        notifications: list[Notification] = Notification.objects.filter(
            user=self.user, show_on_profile=False)
        for notification in notifications:
            if not notification.read:
                return True
        return False

    def get_link(self) -> str:
        manager = DynamicLinkManager()
        return manager.create_link(item_id=self.id, link_type="user")

    def follow(self, user: User) -> 'Profile':
        from api.tasks import reward_and_notify
        from api.notifications import engage_notification

        try:
            Follow.objects.get(follower=user, followee=self.user)\
                .toggle_following()
        except ObjectDoesNotExist:
            if self.is_private:
                follow: Follow = Follow.objects.create(
                    follower=user, followee=self.user,
                    follow_status=Follow.Status.REQUEST_SENT_FIRST)
                engage_notification(
                    follow.followee, follow.follower,
                    "follow_request", follow.follower.id)
            else:
                follow: Follow = Follow.objects.create(
                    follower=user, followee=self.user,
                    follow_status=Follow.Status.FOLLOWING)
                reward_and_notify(
                    follow.followee, follow.follower,
                    "follow", follow.follower.id
                )
        return self

    def save(self, *args, **kwargs):
        if self.title == "":
            self.title = self.user.username
        super(Profile, self).save(*args, **kwargs)


class Community(Subject):
    master_community = models.ForeignKey(
        "self",
        on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
    short_description = models.CharField(max_length=200)

    def get_members(self) -> QuerySet[RoledUser]:
        return RoledUser.objects.exclude(privilege=0)\
            .filter(community=self).order_by('-privilege')

    def get_founder(self) -> User:
        return self.get_members().order_by('id').first().user

    def get_posts(self, *, cls: type = MasterPost) -> QuerySet[MasterPost]:
        posts = cls.objects.filter(community=self).order_by("-date_posted")
        if self.master_community is not None:
            posts = posts | self.master_community.get_posts()
        return posts

    def get_sub_communities(self) -> QuerySet['Community']:
        return Community.objects.filter(master_community=self)

    def is_joined(self, user: User) -> bool:
        from recommender.models import RoledUser

        try:
            RoledUser.objects.get(
                user=user,
                community=self,
                privilege__gte=RoledUser.Roles.member,
                is_banned=False
            )
            return True
        except:
            return False

    def edit(self, updated_attributes: dict) -> None:
        updated_about: str = updated_attributes.get('about', self.about)
        updated_description: str = updated_attributes.get(
            'description', self.short_description)
        updated_info: dict = updated_attributes.get('info', self.info)
        updated_image: ContentFile | str = updated_attributes.get(
            'image', self.image)
        updated_banner: ContentFile | str = updated_attributes.get(
            'banner', self.banner)

        if type(updated_image) == str:
            updated_image = process_base64_image(updated_image)
        if type(updated_banner) == str:
            updated_banner = process_base64_image(updated_banner)

        self.image = updated_image
        self.banner = updated_banner
        self.short_description = updated_description
        self.about = updated_about
        self.info = updated_info
        self.save()

    def change_role(self, other_user_id: int, updated_role: str) -> None:
        other_user: RoledUser = get_object_or_404(
            RoledUser, user__id=other_user_id, community=self)
        other_user.set_role(updated_role)

    def ban_user(self, other_user_id: int) -> None:
        other_user: RoledUser = get_object_or_404(
            RoledUser, user__id=other_user_id, community=self)
        other_user.ban()

    @staticmethod
    def remove_post(post_id: int) -> None:
        post: MasterPost = get_object_or_404(MasterPost, id=post_id)
        post.community = None
        post.save()

    def get_link(self) -> str:
        manager = DynamicLinkManager()

        return manager.create_link(item_id=self.id, link_type="community")

    def join(self, user: User) -> bool:
        if RoledUser.objects.filter(user=user, community=self).exists():
            RoledUser.objects\
                .get(user=user, community=self).toggle_membership()
        else:
            RoledUser.objects.create(user=user, community=self)
        return True

    def to_dict(self) -> dict[str: str | int] | None:
        return {
            'title': self.title,
            'id': self.id,
            'members': self.get_members().count(),
            'sub_communities': self.get_sub_communities().count(),
            'posts': self.get_posts().count(),
            'description': self.short_description,
            'image': self.image.url
        }
