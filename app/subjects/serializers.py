
from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from api.helper import get_profile_image
from api.models import Notification
from api.serializers import Base64ImageField
from blog.models import EventPost, FundablePost
from chain.level import ChainManager
from subjects.models import Profile, Subject, Community
from blog.models import MasterPost
from recommender.models import Follow


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class SmallProfileSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    @staticmethod
    def get_image(obj: User) -> str | None:
        return get_profile_image(obj)

    class Meta:
        model = User
        fields = 'username', 'id', 'image'


class SmallCommunitySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    master = serializers.SerializerMethodField()

    @staticmethod
    def get_image(obj: Community) -> str | None:
        return obj.image.url if obj.image else None

    @staticmethod
    def get_master(obj: Community) -> str | None:
        return obj.master_community.title \
            if obj.master_community is not None else None

    class Meta:
        model = Community
        fields = 'id', 'title', 'image', 'master'


class StoryProfileSerializer(SmallProfileSerializer):
    title = serializers.SerializerMethodField()

    @staticmethod
    def get_title(obj: User) -> str:
        return obj.profile.title

    class Meta(SmallProfileSerializer.Meta):
        fields = SmallProfileSerializer.Meta.fields + ('title',)


class SubjectSerializer(serializers.ModelSerializer):
    image = Base64ImageField(max_length=None, use_url=True, allow_null=True)
    banner = Base64ImageField(max_length=None, use_url=True, allow_null=True)
    posts = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["id", "title", "info", "about", "image", "banner", "posts"]


class ProfileSerializer(SubjectSerializer):
    id = serializers.SerializerMethodField()
    following = serializers.SerializerMethodField()
    followers = serializers.SerializerMethodField()
    posts = serializers.SerializerMethodField()
    communities = serializers.SerializerMethodField()
    attending = serializers.SerializerMethodField()
    contributing = serializers.SerializerMethodField()

    interests = serializers.SerializerMethodField()

    general_attributes = serializers.SerializerMethodField()

    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")

    image = Base64ImageField(max_length=None, use_url=True, allow_null=True)
    banner = Base64ImageField(max_length=None, use_url=True, allow_null=True)

    chain_details = serializers.SerializerMethodField()

    @staticmethod
    def get_id(obj: Profile) -> int:
        return obj.user.id

    @staticmethod
    def follow_status(user: User, obj: Profile) -> int:
        try:
            return Follow.objects\
                .get(follower__id=user.id, followee=obj.user).get_status()
        except ObjectDoesNotExist:
            return Follow.Status.NOT_FOLLOWING

    def get_general_attributes(self, obj: Profile) -> dict:
        request_user = self.context['request'].user
        return {
            'username': obj.user.username,
            'is_private': obj.is_private,
            'is_owner': request_user == obj.user,
            'follow_status': self.follow_status(request_user, obj)
        }

    @staticmethod
    def get_following(obj: Profile) -> int:
        return obj.get_following().count()

    @staticmethod
    def get_followers(obj: Profile) -> int:
        return obj.get_followers().count()

    @staticmethod
    def get_posts(obj: Profile) -> int:
        return MasterPost.objects.filter(author=obj.user).count()

    @staticmethod
    def get_communities(obj: Profile) -> int:
        return obj.get_joined_communities_roles().count()

    @staticmethod
    def get_attending(obj: Profile) -> int:
        return EventPost.attendies.through.objects.filter(user=obj.user).count()

    @staticmethod
    def get_contributing(obj: Profile) -> int:
        return FundablePost\
            .contributers.through.objects.filter(user=obj.user).count()

    @staticmethod
    def get_interests(obj: Profile) -> list[dict]:
        from blog.serializers import TagSerializer

        return TagSerializer(obj.get_interests(), many=True).data

    @staticmethod
    def get_chain_details(obj: Profile) -> dict | None:
        if not obj.user.chainpage.is_verified():
            return None
        try:
            return {
                'balance': str(ChainManager().call(
                    ChainManager.Functions.BALANCE_OF,
                    obj.user.chainpage.wallet_address
                )),
                'address': obj.user.chainpage.wallet_address
            }
        except Exception as e:
            print(e)
            return None

    class Meta(SubjectSerializer.Meta):
        model = Profile
        fields = SubjectSerializer.Meta.fields + [
            'user', 'communities', 'attending', 'general_attributes',
            'interests', 'contributing', 'following', 'followers', 'is_private',
            'gender', 'address', 'first_name', 'last_name', 'chain_details'
        ]


class CommunitySerializer(SubjectSerializer):
    is_joined = serializers.SerializerMethodField()
    sub_communities = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    founder = serializers.SerializerMethodField()
    master_community_info = serializers.SerializerMethodField()

    def get_is_joined(self, obj: Community):
        user = self.context["request"].user
        if user.is_anonymous:
            return False
        return obj.get_members().filter(user=user).exists()

    @staticmethod
    def get_posts(obj: Community):
        return obj.get_posts().count()

    @staticmethod
    def get_members(obj: Community) -> int:
        return obj.get_members().count()

    @staticmethod
    def get_founder(obj: Community) -> dict:
        founder: User = obj.get_founder()
        return SmallProfileSerializer(founder).data

    @staticmethod
    def get_master_community_info(obj: Community) -> dict | None:
        if not obj.master_community:
            return None
        return SmallCommunitySerializer(obj.master_community).data

    @staticmethod
    def get_sub_communities(obj: Community) -> int:
        return obj.get_sub_communities().count()

    class Meta(SubjectSerializer.Meta):
        model = Community
        fields = SubjectSerializer.Meta.fields + [
            "is_joined", "members", 'short_description',
            "sub_communities", "master_community",
            "master_community_info", "founder"
        ]


class NotificationSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    @staticmethod
    def get_data(obj: Notification):
        return obj.data

    @staticmethod
    def get_time(obj: Notification):
        return obj.date_created

    class Meta:
        model = Notification
        fields = 'data', 'time'
