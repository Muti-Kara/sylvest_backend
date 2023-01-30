from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class ChainProfile(models.Model):
    like_reward = models.PositiveSmallIntegerField(default=5)
    comment_like_reward = models.PositiveSmallIntegerField(default=3)
    join_reward = models.PositiveSmallIntegerField(default=10)
    follow_reward = models.PositiveSmallIntegerField(default=10)
    attend_reward = models.PositiveSmallIntegerField(default=20)
    contribute_reward = models.PositiveSmallIntegerField(default=20)

    verification_per_level = models.PositiveSmallIntegerField(default=5)
    token_per_verification = models.PositiveSmallIntegerField(default=5)
    target_approval_number = models.PositiveSmallIntegerField(default=3)

    def __str__(self) -> str:
        return f"Chain Profile {self.id}"

    def to_dict(self) -> dict:
        return {
            'like': self.like_reward,
            'comment_like': self.comment_like_reward,
            'join': self.join_reward,
            'follow': self.follow_reward,
            'attend': self.attend_reward,
            'contribute': self.contribute_reward,
            'verification': self.verification_per_level,
            'token': self.token_per_verification,
            'approval': self.target_approval_number
        }

    def get_reward(self, action: str) -> int:
        return self.to_dict()[action]


class ChainConfig(SingletonModel):
    profile = models.ForeignKey(ChainProfile, on_delete=models.DO_NOTHING)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.JSONField()
    read = models.BooleanField(default=False)
    show_on_profile = models.BooleanField(default=False)
    date_created = models.DateTimeField(default=timezone.now)
    item_id = models.CharField(null=True, blank=True, max_length=100)

    def __str__(self) -> str:
        return f"to: {self.user.username}"
