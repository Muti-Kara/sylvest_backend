from django.contrib.auth.models import User
from rest_framework import serializers

from recommender.models import RoledUser


class RoledUserSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    @staticmethod
    def get_username(obj: RoledUser) -> str:
        return obj.user.username

    @staticmethod
    def get_image(obj: RoledUser) -> str:
        return obj.user.profile.image.url if obj.user.profile.image else None

    @staticmethod
    def get_role(obj: RoledUser):
        return obj.get_role()

    def get_allowed_actions(self, obj: RoledUser) -> list:
        user: User = self.context['request'].user
        if user == obj.user:
            return []
        actions = ['roles', 'users|ban']
        try:
            rolled_request_user: RoledUser = RoledUser.objects.get(
                user=user, community=obj.community
            )
        except Exception as e:
            print(e)
            return []
        return [
            action for action in actions
            if rolled_request_user.can_do(action.split("|")[0])
        ]

    class Meta:
        model = RoledUser
        fields = ["user", "id", "community", "privilege", "username",
                  "image", "role", "allowed_actions"]
