from rest_framework import serializers
from .level import ChainManager
from subjects.serializers import SmallProfileSerializer
from .models import TransferRequest, ChainPage
from django.contrib.auth.models import User


class ChainPageSerializer(serializers.ModelSerializer):
    current_xp = serializers.SerializerMethodField()
    target_xp = serializers.SerializerMethodField()
    chain_attributes = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    @staticmethod
    def get_current_xp(obj: ChainPage) -> int:
        return obj.get_current_xp()

    @staticmethod
    def get_id(obj: ChainPage) -> int:
        return obj.user.id

    @staticmethod
    def get_target_xp(obj: ChainPage) -> int:
        return obj.get_target_xp()

    @staticmethod
    def get_chain_attributes(obj: ChainPage) -> dict:
        return ChainManager().chain_attributes(obj.wallet_address).__dict__()

    class Meta:
        model = ChainPage
        fields = 'url', 'id', 'level', 'staked_level', 'chain_attributes', \
                 'wallet_address', 'current_xp', 'target_xp', 'user', \
                 'verifications', 'verified_state'


class TransferableUserSerializer(SmallProfileSerializer):
    wallet_address = serializers.SerializerMethodField()

    @staticmethod
    def get_wallet_address(obj: User) -> str:
        return obj.chainpage.wallet_address

    class Meta:
        model = User
        fields = SmallProfileSerializer.Meta.fields + ('wallet_address',)


class TransferRequestSerializer(serializers.ModelSerializer):
    is_verified = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    verified_num = serializers.SerializerMethodField()

    def get_is_verified(self, obj: TransferRequest):
        user: User = self.context['request'].user
        return obj.verified_by.all().contains(user)

    @staticmethod
    def get_amount(obj: TransferRequest) -> str:
        return str(obj.amount)

    def get_verified_num(self, obj: TransferRequest):
        return obj.verified_by.count()

    class Meta:
        model = TransferRequest
        fields = "id", "from_addr", "to_addr", "amount", \
                 "verified_num", "is_verified"
