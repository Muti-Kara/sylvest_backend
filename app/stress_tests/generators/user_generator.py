from django.contrib.auth.models import User
from django.core.files.base import ContentFile

from stress_tests.generators.content_generator import ModelGenerator
from stress_tests.generators.random_generators import RandomFilePicker, RandomNameGenerator


class UserGenerator(ModelGenerator):
    __name_generator: RandomNameGenerator
    __file_generator: RandomFilePicker

    def __init__(self):
        self.__name_generator = RandomNameGenerator(r"collections/usernames")
        self.__file_generator = RandomFilePicker(r"collections/photos")
        super(UserGenerator, self).__init__(User)

    def generate(self, number: int, **kwargs) -> list[User]:
        generated: list[User] = []
        password: str = kwargs.get("password", "cCcRrRcCc")
        for i in range(number):
            username = f"{self.__name_generator.get_item()}{self.last_id}"
            user: User = User.objects.create_user(
                username=username,
                password=password,
                email=f"generated{self.last_id}@mail.com"
            )
            self.last_id += 1

            user.unapproveduser.verify()

            print(self.__file_generator.get_item())

            with open(self.__file_generator.get_item(), "rb") as f:
                user.profile.image.save(
                    name=f"{user}profile{i}.png",
                    content=ContentFile(f.read())
                )
            with open(self.__file_generator.get_item(), "rb") as f:
                user.profile.banner.save(
                    name=f"{user}banner{i}.png",
                    content=ContentFile(f.read())
                )
            print("generated: " + str(i) + " " + user.username)
            generated.append(user)
        return generated
