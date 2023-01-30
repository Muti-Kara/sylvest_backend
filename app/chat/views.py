from typing import Callable

from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import QuerySet

from api.helper import process_base64_image
from .models import Room, Message
from .serializers import MessageSerializer, RoomSerializer, SmallRoomSerializer
from .permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly, IsParticipant
from .manager import (
    get_or_create_group,
    get_or_create_room,
    get_lobby_rooms,
    get_unread_messages,
    get_saved_messages,
    get_room_participants,
    read_message,
    save_message
)


class MessageViewSet(ModelViewSet):
    queryset = Message.objects.all()
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
    serializer_class = MessageSerializer

    def list(self, request, *args, **kwargs) -> Response:
        user: User = request.user
        room_id: int = request.query_params.get('room', 1)
        print(room_id)
        message_action: str = request.query_params.get('action', 'unread')
        index: int = request.query_params.get('index', 0)
        chat_room: Room = get_object_or_404(Room, id=room_id)
        if user.is_anonymous:
            return Response({
                'error': 'unauthorized'
            }, status=401)
        match message_action:
            case 'unread':
                messages: QuerySet[Message] = get_unread_messages(chat_room, user, read=True)
            case 'saved':
                print("saved")
                messages: QuerySet[Message] = get_saved_messages(chat_room, int(index))
            case _:
                raise Exception(f'Unexpected action: {message_action}')
        return Response(MessageSerializer(
            messages,
            many=True,
            context={'request': request}
        ).data)

    def partial_update(self, request, pk=None, *args, **kwargs) -> Response:
        commands: dict[str: Callable[[Message, User], any]] = {
            'read_message': read_message,
            'save_message': save_message
        }
        user: User = request.user
        update_action: str = request.data['action']
        message: Message = get_object_or_404(Message, id=pk)
        if update_action not in commands.keys():
            raise Exception(f"Action not recognized: {update_action}")
        commands[update_action](message, user)

        return Response(
            MessageSerializer(message).data
        )

    def perform_create(self, serializer: MessageSerializer) -> None:
        serializer.save(author=self.request.user)


class RoomViewSet(ModelViewSet):
    queryset = Room.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    serializer_class = RoomSerializer

    def list(self, request, *args, **kwargs):
        user: User = request.user
        if user.is_anonymous:
            return Response({
                'error': 'unauthorized'
            }, status=403)
        rooms: QuerySet[Room] = get_lobby_rooms(user)
        return Response(RoomSerializer(
            rooms, many=True, context={
                'request': request
            }
        ).data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        user: User = request.user
        group_action: str = request.data['action']
        group_room: Room = get_object_or_404(Room, id=pk)
        match group_action:
            case 'leave':
                group_room.remove_user_from_group(user)
                return Response({'detail': 'removed'})
            case 'add':
                new_user_id = request.data['new_user']
                new_user = get_object_or_404(User, id=new_user_id)
                group_room.add_user_to_group(new_user)
            case 'remove':
                removed_user_id = request.data['removed_user']
                removed_user = get_object_or_404(User, id=removed_user_id)
                group_room.remove_user_from_group(removed_user)
            case 'edit':
                new_image_data: str | None = request.data['image']
                new_description: str | None = request.data['description']
                new_title: str | None = request.data['title']
                if new_image_data:
                    group_room.image = process_base64_image(new_image_data)
                if new_description:
                    group_room.description = new_description
                if new_title and not group_room.community:
                    group_room.title = new_title
                group_room.save()
            case _:
                raise Exception(f"Action not expected: {group_action}")
        return Response(
            RoomSerializer(group_room, context={
                'request': request
            }).data
        )

    @action(detail=False, methods=['POST'], permission_classes=[IsAuthenticated])
    def get_or_create_p2p(self, request: Request):
        self.check_permissions(request)
        user: User = request.user
        target_username: str = request.data['target']
        target: User = get_object_or_404(User, username=target_username)
        chat_room = get_or_create_room(user=user, target=target)
        return Response(
            RoomSerializer(chat_room, context={
                'request': request
            }).data
        )

    @action(detail=False, methods=['POST'], permission_classes=[IsAuthenticated])
    def get_or_create_group(self, request: Request):
        self.check_permissions(request)
        user: User = request.user
        title: str = request.data['title']
        community_id: int | None = request.data['community_id']
        image_data: str | None = request.data['image']
        participants: list[User] = \
            list(User.objects.filter(id__in=request.data['participants']))
        chat_room = get_or_create_group(
            user, community_id, title, participants, image_data)
        return Response(
            RoomSerializer(chat_room, context={
                'request': request
            }).data
        )

    @action(detail=True, methods=['GET'], permission_classes=[IsParticipant])
    def participants(self, request: Request, pk=None) -> Response:
        chat_room: Room = get_object_or_404(Room, id=pk)
        self.check_object_permissions(request, chat_room)
        return Response(
            get_room_participants(chat_room)
        )

    @action(detail=True, methods=['POST'], permission_classes=[IsParticipant])
    def collect_reward(self, request: Request, pk: int = None) -> Response:
        chat_room: Room = get_object_or_404(Room, id=pk)
        self.check_object_permissions(request, chat_room)
        chat_room.streak.collect_reward()
        return Response(
            RoomSerializer(chat_room, context={'request': request}).data
        )
        
    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def recommended_chats(self, request: Request) -> Response:
        self.check_permissions(request)
        chats: list[Room] = Room.get_active_chats(request.user)
        return Response(
            SmallRoomSerializer(chats, many=True, context={'request': request}).data
        )
        
    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def get_room(self, request: Request) -> Response:
        self.check_permissions(request)
        title: str | None = request.query_params.get("title")
        chats: list[Room] = Room.get_active_chats(request.user)
        for chat in chats:
            if chat.title == title:
                return Response(RoomSerializer(chat, context={'request': request}).data)
        return Response({'detail': 'not found'}, status=404)

