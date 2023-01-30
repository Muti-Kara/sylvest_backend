from rest_framework import permissions
from rest_framework.request import Request

from .models import Message, Room


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request: Request, view, obj: Message):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.author == request.user


class IsParticipant(permissions.BasePermission):
    def has_object_permission(self, request: Request, view, obj: Room):
        return obj.participants.contains(request.user)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request: Request, view, obj: Room):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.admin == request.user
