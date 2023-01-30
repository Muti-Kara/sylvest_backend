from django.contrib.auth.models import User
from django.db import models

actions = {
    "message":  0b000000010,
    "post_c":   0b000000100,
    "post_d":   0b000001000,
    "about":    0b000010000,
    "users":    0b000100000,
    "roles":    0b001000000,
    "admin":    0b010000000,
    "coin":     0b100000000,
}


class RoledUser(models.Model):
    class Roles(models.IntegerChoices):
        not_member =    0b000000000, "Not a member"
        none =          0b000000001, "None"
        member =        0b000000111, "Member"
        moderator =     0b000011111, "Moderator"
        executive =     0b001111111, "Executive"
        admin =         0b111111111, "Admin"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey("subjects.Community", on_delete=models.CASCADE)
    privilege = models.IntegerField(default=Roles.member, choices=Roles.choices)
    is_banned = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user.username} in {self.community.title}"

    def toggle_membership(self):
        if self.privilege > 0:
            self.privilege = self.Roles.not_member
        else:
            self.privilege = self.Roles.member
        self.save()
        return self.privilege

    def ban(self):
        self.is_banned = True
        self.privilege = self.Roles.not_member
        self.save()

    def can_do(self, action: str) -> bool:
        return (not self.is_banned) and (action in actions) and bool(self.privilege & actions[action])

    def set_role(self, role: str) -> bool:
        for role_int, roles in self.Roles.choices:
            if role == roles.lower():
                self.privilege = role_int
                self.save()
                return True
        return False

    def get_role(self) -> str:
        return self.get_privilege_display()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Follow(models.Model):
    class Status(models.IntegerChoices):
        NOT_FOLLOWING = 0
        REQUEST_SENT = 1
        FOLLOWING = 2
        UNFOLLOWED = 3
        REQUEST_SENT_FIRST = 4

    follower = models.ForeignKey(User, related_name="followers", on_delete=models.CASCADE)
    followee = models.ForeignKey(User, related_name="receivers", on_delete=models.CASCADE)
    follow_status = models.IntegerField(choices=Status.choices)

    def toggle_following(self) -> None:
        match self.follow_status:
            case self.Status.REQUEST_SENT:
                self.follow_status = self.Status.NOT_FOLLOWING
            case self.Status.FOLLOWING:
                self.follow_status = self.Status.UNFOLLOWED
            case self.Status.UNFOLLOWED | self.Status.NOT_FOLLOWING:
                if not self.followee.profile.is_private:
                    self.follow_status = self.Status.FOLLOWING
                else:
                    from api.notifications import engage_notification
                    engage_notification(
                        self.followee, self.follower,
                        "follow_request", self.follower.profile.id)
                    self.follow_status = self.Status.REQUEST_SENT
        self.save()

    def accept_follow(self) -> None:
        if self.follow_status == self.Status.NOT_FOLLOWING:
            return
        if self.follow_status == self.Status.REQUEST_SENT_FIRST:
            from api.tasks import reward_and_notify
            reward_and_notify(
                self.followee, self.follower,
                "follow", self.follower.profile.id
            )
        self.follow_status = self.Status.FOLLOWING
        self.save()

    def decline_follow(self) -> None:
        if self.follow_status == self.Status.REQUEST_SENT_FIRST:
            self.delete()
        elif self.follow_status == self.Status.REQUEST_SENT:
            self.follow_status = self.Status.NOT_FOLLOWING
            self.save()

    def get_status(self) -> int:
        if self.follow_status == self.Status.REQUEST_SENT_FIRST:
            return self.Status.REQUEST_SENT
        return self.follow_status


class UserPostRelation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey("blog.MasterPost", on_delete=models.CASCADE)
    is_liked = models.BooleanField()

    def toggle_like(self) -> bool:
        self.is_liked = not self.is_liked
        self.save()
        return self.is_liked


class CommentLike(models.Model):
    comment = models.ForeignKey("blog.Comment", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class FundableContribute(models.Model):
    fundable = models.ForeignKey("blog.FundablePost", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class EventAttend(models.Model):
    event = models.ForeignKey("blog.EventPost", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class PostComment(models.Model):
    post = models.ForeignKey("blog.MasterPost", on_delete=models.CASCADE)
    comment = models.ForeignKey("blog.Comment", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
