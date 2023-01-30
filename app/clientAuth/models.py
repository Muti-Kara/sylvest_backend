from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.db import models


class UnapprovedUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    url_token = models.CharField(max_length=256)
    expiration = models.DateTimeField(default=datetime.now() + timedelta(days=1))

    def save(self, *args, **kwargs):
        if datetime.now() > self.expiration:
            self.user.delete()
            self.delete()
        super(UnapprovedUser, self).save(*args, **kwargs)

    def verify(self) -> None:
        self.user.is_active = True
        self.user.save()
        self.delete()
