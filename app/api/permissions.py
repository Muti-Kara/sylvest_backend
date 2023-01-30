from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.author == request.user


class IsUserOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.user == request.user


class IsUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        return obj.user == request.user


class PublicOrIsInFollowers(permissions.BasePermission):
    from subjects.models import Profile

    def has_object_permission(self, request, view, obj: Profile) -> bool:
        if not obj.is_private or request.user == obj.user:
            return True
        from recommender.models import Follow
        try:
            return Follow.objects \
                       .get(follower=request.user, followee=obj.user) \
                       .get_status() == Follow.Status.FOLLOWING
        except ObjectDoesNotExist:
            return False


class CanVerify(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        user: User = request.user
        return not user.is_anonymous and user.chainpage.verifications > 0


class IsChainVerified(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        from chain.models import ChainPage

        user: User = request.user
        return not user.is_anonymous \
            and user.chainpage.verified_state == ChainPage.VerifiedState.ACCEPTED
