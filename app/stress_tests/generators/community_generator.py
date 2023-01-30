from subjects.models import Community
from recommender.models import RoledUser
from django.core.files.base import ContentFile
from django.contrib.auth.models import User

from stress_tests.generators.content_generator import ModelGenerator
from stress_tests.generators.random_generators import RandomFilePicker, RandomNameGenerator


class CommunityGenerator(ModelGenerator):
    __name_generator: RandomNameGenerator
    __info_generator: RandomNameGenerator
    __file_generator: RandomFilePicker

    def __init__(self):
        self.__name_generator = RandomNameGenerator(r"collections/community_titles")
        self.__info_generator = RandomNameGenerator(r"collections/lorem_ipsum")
        self.__file_generator = RandomFilePicker(r"collections/photos")
        super(CommunityGenerator, self).__init__(Community)

    def generate(self, number: int, **kwargs) -> list[Community]:
        generated: list[Community] = []
        admin = kwargs.get("admin", User.objects.all().first())
        for i in range(number):
            title = f"{self.__name_generator.get_item()}{self.last_id}"
            info = self.__info_generator.get_item()
            community: Community = Community.objects.create(
                title=title,
                about=info,
                short_description=title
            )
            self.last_id += 1

            RoledUser.objects.create(
                user=admin,
                community=community,
                privilege=RoledUser.Roles.admin
            )

            with open(self.__file_generator.get_item(), "rb") as f:
                community.image.save(
                    name=f"{community}profile{i}.png",
                    content=ContentFile(f.read())
                )
            with open(self.__file_generator.get_item(), "rb") as f:
                community.banner.save(
                    name=f"{community}banner{i}.png",
                    content=ContentFile(f.read())
                )
            print(f"generated {i}: {community}")
            generated.append(community)
        return generated
