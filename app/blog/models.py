import secrets
from location_field.models.plain import PlainLocationField
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.deletion import SET_NULL
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from eth_account import Account
from django.db.models import QuerySet
from api.dynamic_links import DynamicLinkManager

from recommender.models import RoledUser, UserPostRelation
from subjects.exceptions import InsufficientPrivilege, DontHavePrivilege
from api.helper import compress_image, get_profile_image
from chain.level import ChainManager


class PostImage(models.Model):
    image = models.ImageField(upload_to='public/post_images')
    position = models.IntegerField(default=0)

    def __str__(self):
        return f"Post Image at position {self.position}"

    def save(self, *args, **kwargs):
        super(PostImage, self).save()

        compress_image(self.image)


class PostVideo(models.Model):
    video = models.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mov'])],
        upload_to='public/post_videos', null=True, blank=True
    )
    position = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f"Post video {self.video.name}"


class MasterPost(models.Model):
    class Types(models.TextChoices):
        POST = 'PO', _('Post')
        PROJECT = 'PR', _('Project')
        EVENT = 'EV', _('Event')

    class Privacy(models.IntegerChoices):
        PUBLIC = 0, _('Public')
        FOLLOWERS = 1, _('Only Followers')
        COMMUNITY = 2, _('Only Community Members')

    post_type = models.CharField(max_length=2, choices=Types.choices, default=Types.POST)

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey("subjects.Community", on_delete=SET_NULL, null=True, blank=True)
    privacy = models.PositiveSmallIntegerField(default=Privacy.PUBLIC, choices=Privacy.choices)

    title = models.CharField(max_length=100)
    content = models.JSONField()

    images = models.ManyToManyField(PostImage, related_name='post_images', blank=True)
    videos = models.ManyToManyField(PostVideo, related_name='post_videos', blank=True)

    ip = models.GenericIPAddressField(null=True, blank=True)
    region = models.CharField(max_length=100, null=True)
    region_details = models.JSONField(null=True, blank=True)

    date_posted = models.DateTimeField(default=timezone.now)

    def __check_community_privilege(self) -> None:
        try:
            rolled_user: RoledUser = RoledUser.objects.get(
                user=self.author, community=self.community)
        except:
            raise DontHavePrivilege()
        if not rolled_user.can_do("post_c"):
            raise InsufficientPrivilege()

    def __update_location(self) -> None:
        try:
            location = Nominatim(
                user_agent="sardter").reverse(self.region).raw['address']
        except Exception as e:
            print(e)
            location = None
        self.region_details = location

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.community:
            self.__check_community_privilege()
        elif self.privacy == self.Privacy.COMMUNITY:
            return
        self.__update_location()
        super(MasterPost, self).save(*args, **kwargs)

    def get_comments(self) -> QuerySet['Comment']:
        return Comment.objects.filter(post=self)

    def get_likes(self) -> QuerySet[UserPostRelation]:
        return UserPostRelation.objects.filter(post=self, is_liked=True)
    
    def get_link(self) -> str:
        manager = DynamicLinkManager()
        return manager.create_link(item_id=self.id)

    def like(self, user: User) -> bool:
        from recommender.models import UserPostRelation

        if UserPostRelation.objects.filter(user=user, post=self).exists():
            UserPostRelation.objects.get(user=user, post=self).toggle_like()
        else:
            UserPostRelation.objects.create(user=user, post=self, is_liked=True)
        return True

    def to_dict(self) -> dict[str: str | int] | None:
        return {
            'title': self.title,
            'id': self.id,
            'likes': self.get_likes().count(),
            'comments': self.get_comments().count(),
            'author': self.author.username,
            'author_image': get_profile_image(self.author),
            'type': self.post_type,
            'date_posted': str(self.date_posted)
        }


class EventPost(MasterPost):
    type = models.CharField(max_length=3)
    date = models.DateTimeField()
    duration = models.DurationField(null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)
    location = PlainLocationField(based_fields=['location_name'], zoom=7, null=True, blank=True)

    attendies = models.ManyToManyField(User, related_name="attendies", blank=True)

    form_data = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return f'{self.title} Event Post'

    def get_attendees(self) -> QuerySet[User]:
        return self.attendies.all()

    def can_attend(self, attend_date: datetime) -> bool:
        delta: timedelta = self.date - attend_date
        return delta.total_seconds() >= 0

    def attend(self, user: User) -> bool:
        from recommender.models import EventAttend

        if not self.can_attend(datetime.now(timezone.utc)):
            return False
        if self.attendies.filter(id=user.id).exists():
            self.attendies.remove(user)
        else:
            self.attendies.add(user)
            event_attend_exists: bool = EventAttend.objects.filter(
                event=self, user=user).exists()
            if user != self.author and not event_attend_exists:
                EventAttend.objects.create(event=self, user=user)
        return True

    def save(self, *args, **kwargs):
        if not self.location:
            self.location = None
        return super(EventPost, self).save(*args, **kwargs)


class FundablePost(MasterPost):
    address = models.CharField(max_length=200, blank=True)
    key = models.CharField(max_length=200)

    target = models.PositiveBigIntegerField()
    current = models.PositiveBigIntegerField(default=0)
    total_funded = models.PositiveBigIntegerField(default=0)
    minimum_fundable_amount = models.PositiveBigIntegerField(null=True, blank=True)

    contributers = models.ManyToManyField(User, related_name="contributers", blank=True)

    form_data = models.JSONField()

    chain_manager = ChainManager()

    def __str__(self) -> str:
        return f'{self.title} Fundable Post'

    @staticmethod
    def generate_key() -> str:
        return f'{secrets.token_hex(32)}'

    @staticmethod
    def generate_address(key: str) -> str:
        return Account.from_key(key).address

    def get_contributors(self) -> QuerySet[User]:
        return self.contributers.all()

    def save(self, *args, **kwargs):
        if self.address is None or len(self.address) == 0:
            key: str = self.generate_key()
            self.key = f'0x{key}'
            self.address = self.generate_address(key)
        super(FundablePost, self).save(*args, **kwargs)

    def can_retrieve(self, user: User) -> bool:
        return self.author == user

    def can_fund(self, amount: int) -> bool:
        if self.minimum_fundable_amount is None:
            return True
        else:
            return amount >= self.minimum_fundable_amount

    def fund_post(self, user: User, amount: int):
        if not self.can_fund(amount=amount):
            raise Exception(
                f"Can't fund post. Amount ({amount}) is less than "
                f"minimum ({self.minimum_fundable_amount}) fundable amount."
            )

        self.chain_manager.send(
            ChainManager.Functions.SEND_TOKEN,
            user.chainpage.wallet_address,
            self.address, amount
        )

        attributes = self.chain_manager.chain_attributes(self.address)
        self.current = int(attributes.balance)
        self.total_funded += amount / self.chain_manager.exp_decimals()
        self.save()
        return attributes

    def retrieve_from_post(self, user: User):
        if not self.can_retrieve(user=user):
            raise Exception("Can't retrieve. User is not the post author.")

        self.chain_manager.send(
            ChainManager.Functions.SEND_TOKEN,
            self.address,
            user.chainpage.wallet_address,
            self.chain_manager.call("balanceOf", self.address)
        )

        attributes = self.chain_manager.chain_attributes(self.address)
        self.current = int(attributes.balance)
        self.save()
        return attributes

    def contribute(self, user: User) -> bool:
        from recommender.models import FundableContribute

        if self.contributers.filter(id=user.id).exists():
            self.contributers.remove(user)
        else:
            self.contributers.add(user)
            fundable_contribute_exists: bool = FundableContribute.objects.filter(
                fundable=self, user=user).exists()
            if user != self.author and not fundable_contribute_exists:
                FundableContribute.objects.create(fundable=self, user=user)
        return True


class Comment(models.Model):
    post = models.ForeignKey(MasterPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    related_comment = models.ForeignKey('self', blank=True, null=True, on_delete=models.DO_NOTHING)
    content = models.JSONField(null=True)  # sample data: {"paragraphs": ["lol","lol2"], "bullets": ["1","2"]}
    date_posted = models.DateTimeField(default=timezone.now)

    likes = models.ManyToManyField(User, related_name="comment_likes", blank=True)

    def __str__(self):
        return f'{self.author} at {self.post}'

    @property
    def get_likes(self):
        return self.likes.count()

    def like(self, user: User) -> bool:
        from recommender.models import CommentLike

        if self.likes.filter(id=user.id).exists():
            self.likes.remove(user)
        else:
            self.likes.add(user)
            comment_like_exists: bool = CommentLike.objects.filter(
                comment=self, user=user).exists()
            if user != self.author and not comment_like_exists:
                CommentLike.objects.create(comment=self, user=user)

    def save(self, *args, **kwargs):
        super(Comment, self).save(*args, **kwargs)


class FormResponse(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(MasterPost, on_delete=models.CASCADE, related_name='form_response')
    data = models.JSONField()
    file = models.FileField(upload_to='public/form_files', blank=True, null=True)
    sent_token = models.IntegerField(blank=True, null=True)

    date_posted = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.author}'s response to {self.post.title}"

    def save(self, *args, **kwargs) -> None:
        if self.sent_token:
            try:
                project: FundablePost = self.post.fundablepost
                project.fund_post(self.author, self.sent_token)
            except Exception as e:
                print(f"Error while sending token {e}")
        return super(FormResponse, self).save(*args, **kwargs)


class Tag(models.Model):
    title = models.CharField(max_length=50)
    posts = models.ManyToManyField(MasterPost, related_name="tag_posts", blank=True)

    def __str__(self) -> str:
        return self.title

    def get_posts(self) -> QuerySet[MasterPost]:
        return self.posts.all()

    @staticmethod
    def get_post_tags(post: MasterPost) -> list['Tag']:
        return [obj.tag for obj in Tag.posts.through.objects.filter(masterpost=post)]
