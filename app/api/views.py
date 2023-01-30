from rest_framework.decorators import api_view
from rest_framework.response import Response

from .notifications import *


@api_view(['POST'])
def get_or_register_device(request):
    user: User = request.user
    device_data: dict = request.data
    device: FCMDevice = FCMDevice.objects.filter(
        device_id=device_data['device_id'],
        user=user
    ).first()
    if not device:
        device = register_device(user, device_data)
    return Response({
        'device': device.device_id
    })


def register_device(user: User, device_data: dict) -> FCMDevice:
    device: FCMDevice = FCMDevice()
    device.device_id = device_data['device_id']
    device.registration_id = device_data['registeration_token']
    device.type = device_data['type']
    device.name = device_data['name']
    device.user = user
    device.save()
    return device
