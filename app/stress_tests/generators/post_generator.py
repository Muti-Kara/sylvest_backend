from typing import Tuple, Callable

from django.core.files.base import ContentFile
from django.contrib.auth.models import User

from stress_tests.generators.content_generator import ModelGenerator
from blog.models import MasterPost, PostImage, PostVideo
from stress_tests.generators.random_generators import RandomNameGenerator, random_post_type, RandomFilePicker, random_coordinates

from random import randrange
from subjects.models import Community


class PostGenerator(ModelGenerator):
    __title_generator: RandomNameGenerator
    __paragraph_generator: RandomNameGenerator
    __link_generator: RandomNameGenerator

    __image_picker: RandomFilePicker
    __video_picker: RandomFilePicker

    def __init__(self):
        self.__title_generator = RandomNameGenerator("collections/post_titles")
        self.__paragraph_generator = RandomNameGenerator("collections/lorem_ipsum")
        self.__link_generator = RandomNameGenerator("collections/links")
        self.__image_picker = RandomFilePicker("collections/photos")
        self.__video_picker = RandomFilePicker("collections/videos")
        super().__init__(MasterPost)

        self.__blocks: dict[str: Callable] = {
            'paragraph': self.__paragraph,
            'link': self.__link,
            'video': self.__video,
            'images': self.__images
        }

    def __paragraph(self) -> str:
        return self.__paragraph_generator.get_item()

    def __link(self) -> str:
        return self.__link_generator.get_item()

    def __image(self) -> PostImage:
        image = PostImage()
        with open(self.__image_picker.get_item(), "rb") as f:
            image.image.save(
                name=f"post_image_{f.name}.jpg",
                content=ContentFile(f.read())
            )
        return image

    def __images(self) -> Tuple[list[int], list[PostImage]]:
        positions, images = [], []
        for i in range(randrange(1, 10)):
            positions.append(i)
            images.append(self.__image())
        return positions, images

    def __video(self) -> PostVideo:
        video = PostVideo()
        with open(self.__video_picker.get_item(), "rb") as f:
            video.video.save(
                name=f"post_video_{f.name}.mp4",
                content=ContentFile(f.read())
            )
        return video

    @staticmethod
    def __coords() -> str:
        lat, long = random_coordinates()
        return f"{lat},{long}"

    @staticmethod
    def __community(user: User) -> Community | None:
        return None
        # if randrange(0, 3) < 2:
        #     return None
        # communities = [role.community
        #                for role
        #                in user.profile.get_joined_communities_roles()]
        #
        # return communities[
        #     randrange(0, 1_000_000_000_000) % len(communities)
        # ]

    @staticmethod
    def __type() -> str:
        return random_post_type()

    def __get_block(self) -> dict:
        index = randrange(0, len(self.__blocks))
        count = 0
        for key, value in self.__blocks.items():
            if count == index:
                return {
                    'type': key,
                    'data': value()
                }
            count += 1
        return {
            'type': 'paragraph',
            'data': self.__blocks['paragraph']()
        }

    def __get_content(self) -> Tuple[dict, list[PostImage], PostVideo | None]:
        blocks = []
        images = []
        video = None
        for i in range(0, randrange(0, 10)):
            block = self.__get_block()
            if block['type'] == "images":
                for j in range(len(blocks)):
                    if blocks[j]['type'] == "images":
                        blocks.remove(blocks[j])
                        break
                images = block['data'][1]
                block['data'] = block['data'][0]
            if block['type'] == "video":
                for j in range(len(blocks)):
                    if blocks[j]['type'] == "video":
                        blocks.remove(blocks[j])
                        break
                video = block['data']
                block['data'] = 0
            blocks.append(block)
        return {
            'building_blocks': blocks
        }, images, video

    def generate(self, number: int, **kwargs) -> list[MasterPost]:
        user: User = kwargs.get("user")
        if not user:
            raise Exception("User cannot be none")
        content, images, videos = self.__get_content()
        posts = []
        for i in range(number):
            post: MasterPost = MasterPost.objects.create(
                title=self.__title_generator.get_item(),
                author=user,
                community=self.__community(user),
                content=content
            )
            if images:
                post.images.add(*images)
            if videos:
                post.videos.add(videos)
            posts.append(post)
        return posts
