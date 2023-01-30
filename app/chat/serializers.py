from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import QuerySet

from .models import Message, Room, Streak
from api.helper import get_profile_image
from api.serializers import Base64FileField, Base64ImageField


class MessageSerializer(serializers.ModelSerializer):
    author_details = serializers.SerializerMethodField()
    community_details = serializers.SerializerMethodField()
    post_details = serializers.SerializerMethodField()
    image_details = serializers.SerializerMethodField()
    file_details = serializers.SerializerMethodField()
    image = Base64ImageField(max_length=None, use_url=True, allow_null=True)
    file = Base64FileField(max_length=None, use_url=True, allow_null=True)

    @staticmethod
    def get_author_details(obj: Message) -> dict:
        return {
            'username': obj.author.username,
            'image': get_profile_image(obj.author),
            'id': obj.id
        }

    @staticmethod
    def get_post_details(obj: Message) -> dict | None:
        if not obj.post:
            return None
        return obj.post.to_dict()

    @staticmethod
    def get_community_details(obj: Message) -> dict | None:
        if not obj.community:
            return None
        return obj.community.to_dict()

    @staticmethod
    def get_image_details(obj: Message) -> dict[str: str | int] | None:
        if not obj.image:
            return None
        width, height = obj.image.width, obj.image.height
        byte_size = str(obj.image.size)
        return {
            'url': obj.image.url,
            'width': width,
            'height': height,
            'size': byte_size,
            'name': obj.image.name,
        }

    @staticmethod
    def get_file_details(obj: Message) -> dict[str: str | int] | None:
        if not obj.file:
            return None
        return {
            'url': obj.file.url,
            'size': obj.file.size,
            'name': obj.file.name.split('/')[-1]
        }

    class Meta:
        model = Message
        fields = ('id', 'author_details', 'content',
                  'room', 'seen', 'post_details', 'type',
                  'community_details', 'image_details',
                  'post', 'community', 'image', 'file',
                  'file_details', 'saved', 'timestamp')


class StreakSerializer(serializers.ModelSerializer):
    multiplier = serializers.SerializerMethodField()

    @staticmethod
    def get_multiplier(obj: Streak) -> int:
        return (obj.final_date - obj.start_date).days

    class Meta:
        model = Streak
        fields = ('id', 'room', 'multiplier', 'collected_xp', 'start_date', 'final_date')


class RoomSerializer(serializers.ModelSerializer):
    room_details = serializers.SerializerMethodField()
    message_details = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()
    streak_details = serializers.SerializerMethodField()

    @staticmethod
    def __title(user: User, obj: Room, target: User = None) -> str:
        if user.is_anonymous or obj.type == Room.Type.GROUP:
            return obj.title
        return target.username

    @staticmethod
    def __image(obj: Room, target: User) -> str | None:
        if obj.type == Room.Type.GROUP:
            image = obj.image
        else:
            image = target.profile.image
        if not image:
            return None
        return image.url

    @staticmethod
    def __target(obj: Room, user: User) -> User:
        return obj.participants.exclude(id=user.id).first()

    @staticmethod
    def get_streak_details(obj: Room) -> dict:
        return StreakSerializer(obj.streak).data

    def get_message_details(self, obj: Room) -> dict:
        from .manager import get_unread_messages

        user: User = self.context['request'].user
        messages: QuerySet[Message] = get_unread_messages(obj, user)
        return {
            'count': messages.count(),
            'last_message': MessageSerializer(messages.first()).data if messages.first() else None
        }

    def get_allowed_actions(self, obj: Room) -> list[str]:
        user: User = self.context['request'].user
        if obj.type == Room.Type.PEER2PEER or user.is_anonymous:
            return []
        elif obj.community or not obj.admins.contains(user):
            return ['leave']
        else:
            return ['leave', 'remove', 'add', 'edit']

    def get_room_details(self, obj: Room) -> dict[str: str | None]:
        user: User = self.context['request'].user
        target: User = self.__target(obj, user) if obj.type == Room.Type.PEER2PEER else None
        return {
            'title': self.__title(user, obj, target),
            'image': self.__image(obj, target)
        }

    class Meta:
        model = Room
        fields = ('id', 'type', 'image',
                  'room_details', 'message_details',
                  'allowed_actions', 'description',
                  'streak_details')


class SmallRoomSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    room_type = serializers.SerializerMethodField()

    def get_image(self, obj: Room) -> str | None:
        user: User = self.context['request'].user
        if obj.type == Room.Type.GROUP:
            image = obj.image
        else:
            image = obj.participants.exclude(id=user.id).first().profile.image
        if not image:
            return None
        return image.url

    def get_title(self, obj: Room) -> str:
        user: User = self.context['request'].user
        if user.is_anonymous or obj.type == Room.Type.GROUP:
            return obj.title
        return obj.participants.exclude(id=user.id).first().username

    @staticmethod
    def get_room_type(obj: Room) -> str:
        return obj.type

    class Meta:
        model = Room
        fields = 'title', 'image', 'id', 'room_type'
