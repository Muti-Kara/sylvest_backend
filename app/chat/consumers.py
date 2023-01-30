import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User

from channels.db import database_sync_to_async


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ChatConsumer(AsyncWebsocketConsumer, metaclass=Singleton):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.group_name = "sylvest_chat"

    @staticmethod
    @database_sync_to_async
    def user_exists(username: str) -> bool:
        return User.objects.filter(username=username).exists()

    async def send_notification(self, notification):
        await self.send(json.dumps(notification))

    async def connect(self):
        header_dictionary = dict(self.scope['headers'])
        header_dictionary = {key.decode(): val.decode() for key, val in header_dictionary.items()}

        username = header_dictionary['username']

        if await self.user_exists(username):  # prepare a communiacation channel for user
            await self.accept()
            if self.group_name == username:
                return
            await self.send(
                text_data=json.dumps({
                    "type": "connection established!",
                    "message": "You are now connected!"
                }))

            print(f"connected: {username}")
            self.group_name = username
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        else:
            await self.close()

    async def disconnect(self, code):
        if hasattr(self, 'group_name') and self.group_name is not None:
            print(f"Disconnecting: {self.group_name}")
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            self.group_name = None

    # Receive message from WebSocket
    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        print(data)
        # command: str = data['command']
        # if command not in self.commands.keys():
        #     raise Exception(f"Command not recognized: {command}")
        # await self.commands[command](self, data)

    async def send_chat_message(self, message):
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def read_chat_messages(self, data):
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'message_action',
                'content': data
            }
        )

    async def send_message(self, message):
        await self.send(text_data=json.dumps(message))

    async def message_action(self, event):
        content = event['message']
        print("sending action")
        await self.send(text_data=json.dumps(content))

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        print("sending message")
        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))
