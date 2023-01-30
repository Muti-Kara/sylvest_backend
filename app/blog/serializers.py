from rest_framework import serializers
from rest_framework.request import Request

from api.serializers import Base64FileField, Base64ImageField
from chain.level import ChainManager
from blog.models import *
from subjects.serializers import SmallProfileSerializer, StoryProfileSerializer


class PostImageSerializer(serializers.ModelSerializer):
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        model = PostImage
        fields = ['id', 'image', 'position']


class PostVideoSerializer(serializers.ModelSerializer):
    video = Base64FileField(max_length=None, use_url=True)

    class Meta:
        model = PostVideo
        fields = ['id', 'video', 'position']


class MasterPostSerializer(serializers.ModelSerializer):
    author_details = serializers.SerializerMethodField()
    community_details = serializers.SerializerMethodField()
    request_details = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    liked_by_following = serializers.SerializerMethodField()
    event_fields = serializers.SerializerMethodField()
    project_fields = serializers.SerializerMethodField()
    post_form_data = serializers.SerializerMethodField()

    @staticmethod
    def is_contributing(user: User, post: MasterPost) -> bool:
        if post.post_type != MasterPost.Types.PROJECT:
            return False
        project: FundablePost = post.fundablepost
        return project.contributers.contains(user)

    @staticmethod
    def is_attending(user: User, post: MasterPost) -> bool:
        if post.post_type != MasterPost.Types.EVENT:
            return False
        event: EventPost = post.eventpost
        return event.attendies.contains(user)

    @staticmethod
    def is_author(user: User, post: MasterPost) -> bool:
        return user == post.author

    @staticmethod
    def is_liked(user: User, post: MasterPost) -> bool:
        query = UserPostRelation.objects.filter(user=user, post=post)
        if query.exists():
            return query.first().is_liked
        return False

    @staticmethod
    def get_author_details(obj: MasterPost) -> dict:
        return SmallProfileSerializer(obj.author).data

    def get_liked_by_following(self, obj: MasterPost):
        request_user: User = self.context['request'].user
        if request_user.is_anonymous:
            return []
        following = set([
            user for user in request_user.profile.get_following()
        ])
        liked_by = set([
            user_post.user for user_post in
            UserPostRelation.objects.filter(post=obj, is_liked=True)
        ])
        liked_by = list(following.intersection(liked_by))[:3]
        return SmallProfileSerializer(liked_by, many=True).data

    @staticmethod
    def get_comments(obj):
        return Comment.objects.filter(post=obj).count()

    @staticmethod
    def get_likes(obj: MasterPost):
        return UserPostRelation.objects.filter(post=obj, is_liked=True).count()

    @staticmethod
    def get_community_details(obj: MasterPost):
        if obj.community is None:
            return None
        return {
            "title": obj.community.title,
            "id": obj.community.id,
            "image": obj.community.image.url if obj.community.image else None,
        }

    def get_request_details(self, obj: MasterPost):
        user: User = self.context['request'].user
        if user.is_anonymous:
            return {
                "allowed_actions": [],
                "is_liked": False,
                "is_author": False,
                "is_attending": False,
                "is_contributing": False,
                "is_anonymous": True
            }
        allowed_actions = []
        if self.is_author(user, obj): allowed_actions += ['delete', 'update']
        try:
            rolled_user: RoledUser = RoledUser.objects.get(
                user=user, community=obj.community)
            if rolled_user.can_do("post_d"):
                allowed_actions.append('remove_from_community')
        except Exception as e:
            pass
        return {
            "user_details": SmallProfileSerializer(user).data,
            "image": get_profile_image(user),
            "allowed_actions": allowed_actions,
            "is_liked": self.is_liked(user, obj),
            "is_author": self.is_author(user, obj),
            "is_attending": self.is_attending(user, obj),
            "is_contributing": self.is_contributing(user, obj),
            "is_anonymous": False
        }

    def get_event_fields(self, obj: MasterPost) -> dict | None:
        if obj.post_type != MasterPost.Types.EVENT:
            return None
        event: EventPost = obj.eventpost
        return {
            'type': event.type,
            'date': event.date,
            'duration': int(event.duration.total_seconds()) if event.duration else None,
            'location_name': event.location_name,
            'location': event.location,
            'can_attend': event.can_attend(datetime.now(timezone.utc)),
            'attendees': event.attendies.all().count()
        }

    def get_project_fields(self, obj: MasterPost) -> dict | None:
        if obj.post_type != MasterPost.Types.PROJECT:
            return None
        project: FundablePost = obj.fundablepost

        try:
            current_balance: int | None = ChainManager().chain_attributes(
                self.context['request'].user.chainpage.wallet_address).balance
        except Exception as e:
            current_balance = None
        return {
            'target': float(project.target),
            'minimum': float(project.minimum_fundable_amount)
            if project.minimum_fundable_amount else None,
            'current': float(project.current),
            'address': project.address,
            'contributors': project.contributers.all().count(),
            'user_current_balance': str(current_balance) if current_balance is not None else None,
            'total_funded': float(project.total_funded)
        }

    @staticmethod
    def get_post_form_data(obj: MasterPost) -> dict | None:
        if obj.post_type == MasterPost.Types.POST:
            return None
        elif obj.post_type == MasterPost.Types.PROJECT:
            project: FundablePost = obj.fundablepost
            return project.form_data
        else:
            event: EventPost = obj.eventpost
            return event.form_data

    def get_images(self, obj: MasterPost) -> list:
        return PostImageSerializer(
            obj.images.all(), many=True, context={'request': self.context['request']}).data

    def get_videos(self, obj: MasterPost) -> list:
        return PostVideoSerializer(
            obj.videos.all(), context={'request': self.context['request']}, many=True).data

    class Meta:
        model = MasterPost
        fields = ['url', 'id', 'title', 'post_type', 'community',
                  'community_details', 'content',
                  'images', 'ip', 'region', 'likes', 'request_details', 'comments',
                  'author_details', 'liked_by_following',
                  'region_details', 'date_posted', 'event_fields',
                  'project_fields', 'post_form_data', 'videos', 'privacy']


class EventPostSerializer(MasterPostSerializer):
    class Meta(MasterPostSerializer.Meta):
        model = EventPost
        fields = MasterPostSerializer.Meta.fields + [
            'type', 'date', 'duration', 'location_name',
            'location', 'attendies', 'form_data'
        ]


class EventWithLocationSerializer(serializers.ModelSerializer):
    author_details = serializers.SerializerMethodField()
    is_attending = serializers.SerializerMethodField()
    attendies = serializers.SerializerMethodField()

    @staticmethod
    def get_author_details(obj: EventPost) -> dict:
        return SmallProfileSerializer(obj.author).data

    def get_is_attending(self, obj: EventPost) -> bool:
        user: User = self.context['request'].user
        return obj.attendies.all().contains(user)

    @staticmethod
    def get_attendies(obj: EventPost) -> list[dict]:
        return SmallProfileSerializer(obj.attendies.all(), many=True).data

    class Meta:
        model = EventPost
        fields = 'id', 'title', 'date', 'location', 'author_details', 'is_attending', 'attendies'


class FundablePostSerializer(MasterPostSerializer):
    class Meta(MasterPostSerializer.Meta):
        model = FundablePost
        fields = MasterPostSerializer.Meta.fields + [
            'address', 'total_funded', 'target', 'current',
            'minimum_fundable_amount', 'form_data'
        ]


class CommentSerializer(serializers.ModelSerializer):
    author_details = serializers.SerializerMethodField()
    related_comment_author = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    reply_num = serializers.SerializerMethodField()
    request_details = serializers.SerializerMethodField()

    @staticmethod
    def get_author_details(obj: Comment) -> dict:
        return SmallProfileSerializer(obj.author).data

    @staticmethod
    def get_related_comment_author(obj: Comment) -> dict | None:
        if not obj.related_comment:
            return None
        return SmallProfileSerializer(obj.related_comment.author).data

    @staticmethod
    def is_liked(user: User, comment: Comment) -> bool:
        return comment.likes.contains(user)

    @staticmethod
    def is_author(user: User, post: Comment) -> bool:
        return user == post.author

    @staticmethod
    def get_likes(obj: Comment) -> int:
        return obj.get_likes

    @staticmethod
    def get_reply_num(obj: Comment) -> int:
        return Comment.objects.filter(related_comment=obj).count()

    def get_request_details(self, obj: Comment) -> dict:
        user: User = self.context['request'].user
        if user.is_anonymous:
            return {
                "is_liked": False,
                "is_anonymous": True,
                "allowed_actions": [],
                "is_author": False,
                "is_attending": False,
                "is_contributing": False,
            }
        user: User = self.context['request'].user
        allowed_actions = []
        if user == obj.author:
            allowed_actions += ['delete', 'update']
        return {
            "user_details": SmallProfileSerializer(user).data,
            "allowed_actions": allowed_actions,
            "is_liked": self.is_liked(user, obj),
            "is_author": self.is_author(user, obj),
            "is_anonymous": False,
            "is_attending": False,
            "is_contributing": False,
        }

    class Meta:
        model = Comment
        fields = ['id', 'author_details', 'content', 'likes', 'post',
                  'related_comment', 'related_comment_author',
                  'reply_num', 'request_details', 'date_posted']


class FormResponseSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    author_image = serializers.SerializerMethodField()
    file = Base64FileField(allow_null=True)
    file_details = serializers.SerializerMethodField()

    @staticmethod
    def get_author_image(obj: FormResponse) -> str:
        return get_profile_image(obj.author)

    def get_file_details(self, obj: FormResponse) -> dict | None:
        if not obj.file:
            return None
        return {
            'name': obj.file.name.split('/')[-1],
            'url': obj.file.url,
            'size': self.convert_size(obj.file.size),
        }

    @staticmethod
    def convert_size(size_bytes: int) -> str:
        import math

        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    class Meta:
        model = FormResponse
        fields = ['author', 'post', 'data', 'date_posted',
                  'sent_token', 'author_image', 'file', 'file_details']


class TagSerializer(serializers.ModelSerializer):
    posts = serializers.SerializerMethodField()

    @staticmethod
    def get_posts(obj: Tag) -> int:
        return obj.get_posts().count()

    class Meta:
        model = Tag
        fields = 'title', 'posts', 'id'



