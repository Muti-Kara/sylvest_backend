import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sylvest_django.settings")
django.setup()

from generators.user_generator import UserGenerator
from generators.community_generator import CommunityGenerator
from generators.follow_generator import FollowGenerator
from generators.member_generator import MemberGenerator
from generators.post_generator import PostGenerator

user_generator = UserGenerator()
community_generator = CommunityGenerator()
follow_generator = FollowGenerator()
member_generator = MemberGenerator()
post_generator = PostGenerator()

def generate_users(number: int):
    user_generator.generate(number)


def generate_community(number: int):
    community_generator.generate(number)


def generate_followers():
    from django.contrib.auth.models import User

    follow_generator.generate(0, users=User.objects.all())


def generate_members():
    from django.contrib.auth.models import User
    from subjects.models import Community

    member_generator.generate(
        0,
        members=User.objects.all(),
        communities=Community.objects.all()
    )


def generate_posts(number):
    from django.contrib.auth.models import User

    for user in User.objects.all():
        post_generator.generate(number, user=user)


def main():
    user_number = 100
    # generate_users(user_number)
    community_number = 1000
    # generate_community(1000)
    # generate_followers()
    generate_members()
    # generate_posts(100)


if __name__ == "__main__":
    main()
