from datetime import datetime
import json
from decimal import Decimal

from firebase_admin.messaging import Message
from fcm_django.models import FCMDevice
from django.contrib.auth.models import User
from api.helper import get_profile_image
from api.models import Notification
from django.db.models import QuerySet


def notification(
        to: User,
        category: str = "social",
        notification_type: str = None,
        action: str = None,
        item_id: int = None,
        image_url: str = None,
        save_to_profile: bool = False) -> None:

    devices: QuerySet[FCMDevice] = FCMDevice.objects.filter(user=to)
    last_notification: Notification = Notification.objects.last()
    last_id = 0
    if last_notification:
        last_id = last_notification.id
    data: dict[str, str] = {
        'type': notification_type,
        'content': json.dumps({
            'largeIcon': image_url,
            'title': "Sylvest",
            'channelKey': f"{category}_channel",
            "groupKey": f"{category}_group",
            "category": category,
            'body': action,
            "id": last_id + 1,
        }),
        'time': str(datetime.now())
    }
    if item_id:
        data['item_id'] = str(item_id)
    for device in devices:
        device.send_message(Message(data=data))
        print(device.device_id)
    Notification.objects.create(
        data=data,
        user=to,
        show_on_profile=save_to_profile,
        item_id=str(item_id) if item_id else None
    )


def engage_notification(
        to: User,
        sender: User,
        action: str,
        item_id: int) -> None:
    image = get_profile_image(sender)
    action_str: str
    match action.upper():
        case 'LIKE':
            action_str = f'{sender.username} liked your post'
        case 'COMMENT':
            action_str = f'{sender.username} commented on your post'
        case "LIKE_COMMENT":
            action_str = f'{sender.username} liked your comment'
        case "FOLLOW":
            action_str = f'{sender.username} followed you'
        case "FOLLOW_REQUEST":
            action_str = f'{sender.username} wants to follow you'
        case "JOIN":
            action_str = f'{sender.username} joined your community'
        case "CONTRIBUTE":
            action_str = f'{sender.username} is contributing to your post'
        case "ATTEND":
            action_str = f'{sender.username} is attending your event'
        case _:
            raise Exception(f'Action is not valid: {action}')
    notification(
        to=to,
        notification_type=action.lower(),
        item_id=item_id,
        image_url=image,
        action=action_str,
        save_to_profile=True
    )


def text_notification(
        to: User,
        sender: User,
        message_data: str,
        message_type: str) -> None:
    image = get_profile_image(sender)
    action_str: str
    match message_type.lower():
        case 't':
            action_str = f'{sender.username}: {message_data}'
        case 'i':
            action_str = f'{sender.username}: Image File'
        case 'f':
            action_str = f'{sender.username}: File'
        case 'p':
            action_str = f'{sender.username}: Post'
        case 'c':
            action_str = f'{sender.username}: Community'
        case _:
            raise Exception(f'Invalid type: {message_type}')
    notification(
        to=to,
        notification_type="message",
        image_url=image,
        action=action_str,
        category="message"
    )


def level_up_notification(to: User) -> None:
    chain_page = to.chainpage
    action_str = f"Congrats! You now have {chain_page.level} levels!"
    notification(
        to=to,
        notification_type="level_up",
        action=action_str,
        save_to_profile=True
    )


def token_notification(
        to: User, action: str,
        sender: User | None = None,
        amount: Decimal | None = None) -> None:
    def _token_action() -> str:
        match action.lower():
            case 'token':
                return f"{sender.username} just sent you {amount:.2g} SYLK!"
            case 'reward':
                return f"{amount:.2g} SYLK was rewarded!"
            case _:
                raise Exception(f'Type was not expected: {action}')

    action_str = _token_action()
    image = get_profile_image(sender) if sender else None
    notification(
        to=to,
        notification_type=action,
        save_to_profile=True,
        image_url=image,
        action=action_str,
        item_id=sender.id if action == 'token' else None
    )


def new_post_notification(to: User, sender: User, post_id: int, post_title: str) -> None:
    action_str = f"{sender.username} just published a new post: {post_title}"
    image = get_profile_image(sender)
    notification(
        to=to,
        notification_type="follower_post",
        image_url=image,
        action=action_str,
        item_id=post_id
    )
