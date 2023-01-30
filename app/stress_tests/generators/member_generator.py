from recommender.models import RoledUser
from django.contrib.auth.models import User
from subjects.models import Community

from stress_tests.generators.content_generator import ModelGenerator

from random import randrange


class MemberGenerator(ModelGenerator):
    def __init__(self):
        super(MemberGenerator, self).__init__(RoledUser)

    def generate(self, number: int, **kwargs) -> list[RoledUser]:
        members: list[User] = kwargs.get("members")
        communities: list[Community] = kwargs\
            .get("communities", Community.objects.all())
        if not members or not communities:
            raise Exception("Members or communities cannot be none or empty")
        joined_members = []
        for community in communities:
            for potential_member in members:
                if randrange(1, 101) < 50:
                    continue
                member = RoledUser.objects.create(
                    user=potential_member,
                    community=community,
                    privilege=RoledUser.Roles.choices[randrange(0, 6)][0]
                )
                joined_members.append(member)
        return joined_members
