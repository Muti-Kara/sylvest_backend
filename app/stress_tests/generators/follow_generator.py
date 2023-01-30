from recommender.models import Follow
from django.contrib.auth.models import User

from stress_tests.generators.content_generator import ModelGenerator

from random import randrange


class FollowGenerator(ModelGenerator):
    def __init__(self):
        super(FollowGenerator, self).__init__(Follow)
    
    def generate(self, number: int, **kwargs) -> list[Follow]:
        users: list[User] = kwargs.get("users")
        if not users:
            raise Exception("Users cannot be none or empty")
        follows = []
        for user in users:
            for potential_followee in users:
                if randrange(1, 101) < 50:
                    continue
                follow = Follow.objects.create(
                    follower=user,
                    followee=potential_followee,
                    follow_status=Follow.Status.FOLLOWING
                )
                follows.append(follow)
        return follows

