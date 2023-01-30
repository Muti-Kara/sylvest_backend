import asyncio
from typing import Iterable

from channels.layers import get_channel_layer, InMemoryChannelLayer
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models import QuerySet, ObjectDoesNotExist

from api.helper import process_base64_image, get_profile_image
from subjects.models import Community
from .models import Room, Message

layer: InMemoryChannelLayer = get_channel_layer()


async def send_message_to_layer(participants: list[str], message: dict) -> None:
    await asyncio.gather(*[layer.group_send(participant, {
        'type': 'chat_message',
        'message': {
            'command': 'new_message',
            'content': message
        }
    }) for participant in participants])


async def message_action_to_layer(
        participants: list[str],
        message_id: int,
        room_id: int,
        action: str = 'seen') -> None:
    await asyncio.gather(*[layer.group_send(participant, {
        'type': 'message_action',
        'message': {
            'command': f'message_{action}',
            'content': {
                'message_id': message_id,
                'room_id': room_id
            }
        }
    }) for participant in participants])


def read_messages(messages: Iterable[Message], user: User) -> None:
    for message in messages:
        read_message(message, user)


def read_message(message: Message, user: User) -> None:
    message.seen_by.add(user)
    message.save()


def save_message(message: Message, user: User) -> None:
    message.saved = True
    message.save()


def get_unread_messages(room: Room, user: User, read: bool = False) -> QuerySet[Message]:
    messages: QuerySet[Message] = Message.objects\
        .filter(room=room)\
        .exclude(seen_by__in=[user])\
        .order_by('-timestamp')
    if read:
        read_messages(messages, user)
        room.streak.update_streak()
    return messages


def get_saved_messages(room: Room, index: int = 0) -> QuerySet[Message]:
    messages: QuerySet['Message'] = Message.objects.filter(
        room=room, saved=True
    ).order_by('-timestamp')

    lower_limit: int = room.NUMBER_OF_MESSAGE_PER_FETCH * index
    upper_limit: int = room.NUMBER_OF_MESSAGE_PER_FETCH * (index + 1)
    return messages[lower_limit: upper_limit]


def get_or_create_room(user: User, target: User) -> Room:
    try:
        return Room.objects \
            .filter(participants__in=[user.id], type=Room.Type.PEER2PEER) \
            .get(participants__in=[target.id])
    except ObjectDoesNotExist:
        new_room = Room()
        new_room.title = f'{user}__r00m__{target}'
        new_room.save()
        new_room.participants.add(user)
        new_room.participants.add(target)
        return new_room


def get_or_create_group(
        user: User,
        community_id: int | None,
        room_title: str,
        participants: list[User],
        image_data: str = None,
        image_file: ContentFile = None,
        community: Community = None) -> Room:
    try:
        if community_id is None:
            raise ObjectDoesNotExist()
        return Room.objects \
            .filter(participants__in=[user.id], type=Room.Type.GROUP) \
            .get(community_id=community_id)
    except ObjectDoesNotExist:
        image: ContentFile | None = None
        if image_data:
            image = process_base64_image(image_data)
        elif image_file:
            image = image_file

        new_group = Room(
            title=room_title, type=Room.Type.GROUP,
            image=image, community=community,
        )

        new_group.save()
        new_group.admins.add(user)
        participants.append(user)
        new_group.participants.add(*participants)
        return new_group


def get_lobby_rooms(user: User) -> QuerySet[Room]:
    return Room.objects.filter(participants__in=[user.id])


def get_room_participants(room: Room) -> list[dict[str: int | str | bool]]:
    return [{
        'id': participant.id,
        'username': participant.username,
        'image': get_profile_image(participant),
        'is_admin': room.admins.contains(participant)
    } for participant in room.participants.all()]
