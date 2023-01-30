from datetime import datetime, timedelta

from django.db import models
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from blog.models import MasterPost
from subjects.models import Community
from api.helper import compress_image


class Room(models.Model):
    class Type(models.TextChoices):
        PEER2PEER = 'PP', _('Peer to Peer')
        GROUP = 'GR', _('Group')

    NUMBER_OF_MESSAGE_PER_FETCH = 20

    type = models.CharField(max_length=2, choices=Type.choices, default=Type.PEER2PEER)
    title = models.CharField(max_length=100, default='lobby')
    participants = models.ManyToManyField(User, related_name='room_participants')
    image = models.ImageField(upload_to='public/group_images', null=True, blank=True)
    community = models.ForeignKey(Community, null=True, blank=True, on_delete=models.CASCADE)
    admins = models.ManyToManyField(User, related_name="room_admins")
    description = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return self.title

    @staticmethod
    def get_active_chats(user: User) -> list['Room']:
        return list(Room.objects.filter(participants__in=[user.id]))

    def remove_user_from_group(self, user: User) -> bool:
        if self.type == Room.Type.PEER2PEER:
            raise Exception("Can't remove from peer to peer")
        try:
            self.participants.remove(user)
            if self.participants.count() == 0:
                self.delete()
            elif self.admins.contains(user):
                self.admins.remove(user)
                if self.admins.all().count() == 0:
                    self.admins.add(self.participants.all().first())
            return True
        except Exception as e:
            print(f"Exception during remove of user from group: {e}")
            return False

    def add_user_to_group(self, user: User) -> bool:
        if self.type == Room.Type.PEER2PEER:
            raise Exception("Can't add to peer to peer")
        try:
            self.participants.add(user)
            return True
        except Exception as e:
            print(f"Exception while adding user to group: {e}")
            return False


class Message(models.Model):
    class Type(models.TextChoices):
        TEXT = 'T', _('Text')
        IMAGE = 'I', _('Image')
        FILE = 'F', _('File')
        POST = 'P', _('Post')
        COMMUNITY = 'C', _('Community')

    author = models.ForeignKey(
        User,
        related_name='author_message',
        on_delete=models.CASCADE
    )
    content = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    seen = models.BooleanField(default=False)
    saved = models.BooleanField(default=False)
    seen_by = models.ManyToManyField(User, related_name='message_seen_by', blank=True)
    type = models.CharField(max_length=1, choices=Type.choices, default=Type.TEXT)
    image = models.ImageField(upload_to='public/text_images', blank=True, null=True)
    file = models.FileField(upload_to='public/text_files', blank=True, null=True)
    post = models.ForeignKey(
        MasterPost,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='message_post'
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='message_community'
    )

    def __str__(self) -> str:
        return f'{self.author.username}: {self.content}'

    def save(self, *args, **kwargs):
        super(Message, self).save(*args, **kwargs)

        if self.image is not None:
            compress_image(self.image)


class Streak(models.Model):
    DAILY_MESSAGE_LIMIT: int = 1
    XP_PER_DAY: int = 10

    room = models.OneToOneField(Room, on_delete=models.CASCADE)
    collected_xp = models.PositiveBigIntegerField(default=0)
    start_date = models.DateTimeField(auto_now_add=True)
    final_date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"x{(self.final_date - self.start_date).days} streak of {self.room}"

    def save(self, *args, **kwargs) -> None:
        super(Streak, self).save(*args, **kwargs)

    def calculate_reward(self):
        difference: timedelta = self.final_date - self.start_date
        return self.XP_PER_DAY * min(difference.days, 10)

    def calculate_streak(self, now: datetime = timezone.now()) -> int:
        difference: timedelta = (now - self.final_date)
        yesterday: datetime = now - timedelta(days=1)
        if difference < timedelta(days=1, minutes=-1):
            return 0
        elif difference > timedelta(days=2, minutes=1):
            return -1
        messages: QuerySet[Message] = Message.objects.filter(room=self.room, timestamp__range=[yesterday, now])
        for participant in self.room.participants.all():
            participant_messages: QuerySet[Message] = messages.filter(author=participant)
            if participant_messages.count() < self.DAILY_MESSAGE_LIMIT:
                return 0
        return 1

    def collect_reward(self) -> None:
        for user in self.room.participants.all():
            user.chainpage.get_reward(amount=self.collected_xp)
        self.collected_xp = 0
        self.save()

    def update_streak(self, now: datetime = timezone.now()) -> None:
        streak = self.calculate_streak(now)
        if streak == -1:
            self.start_date = now
            self.final_date = now
        elif streak == 1:
            self.collected_xp = self.collected_xp + self.calculate_reward()
            self.final_date = now
        self.save()
