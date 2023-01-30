import base64
import json
from imghdr import what
from typing import Callable, Tuple
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.core.paginator import Page, Paginator
from django.db.models import QuerySet


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def get_profile_image(user: User) -> str | None:
    return user.profile.image.url if user.profile.image else None


def compress_image(
        image_file: ImageFile,
        down_size: bool = False,
        down_size_width: int = None) -> None:
    return

    # with image_file.open('rb') as f:
    #     image: Image = Image.open(f)
    #
    # if down_size:
    #     output_size = (down_size_width, down_size_width)
    #     image.thumbnail(output_size, Image.ANTIALIAS)
    #
    # with image_file.open('wb') as f:
    #     image.save(f, optimize=True, quality=85)
    # image.close()


def generate_random_name() -> str:
    return str(uuid4())[:12]


def get_image_extension(image_name: str, decoded_file: bytes) -> str:
    extension = what(image_name, decoded_file)
    extension = "jpg" if extension == "jpeg" else extension
    return extension


def process_base64_image(
        data: str,
        on_error: Callable[[str], any] = None
        ) -> ContentFile:
    if 'data:' in data and ';base64,' in data:
        header, data = data.split(';base64,')
    try:
        decoded_file = base64.b64decode(data)
    except TypeError:
        if on_error:
            on_error('invalid_image')
        raise Exception("invalid image type")
    name = generate_random_name()
    extension = get_image_extension(name, decoded_file)
    complete_name = f"{name}.{extension}"
    content = ContentFile(decoded_file, complete_name)
    if content.size > 5242880:
        if on_error:
            on_error('invalid_file')
        raise Exception("File cannot be larger than 50mb")
    return content


def process_base64_file(
        data: str | dict,
        on_error: Callable[[str], any] = None
        ) -> ContentFile:
    print("here")
    json_file: dict = data if type(data) == dict else json.loads(data)
    file: str = json_file['file']
    extension: str = json_file['extension']
    if 'data:' in file and ';base64,' in file:
        header, file = file.split(';base64,')

    try:
        decoded_file: bytes = base64.b64decode(file)
    except TypeError:
        print("TYPE ERROR")
        if on_error:
            on_error('invalid_file')
        raise Exception("invalid file type")

    file_name: str = json_file.get('name', generate_random_name())
    complete_name: str = f"{file_name}{extension}"
    content = ContentFile(decoded_file, complete_name)
    if content.size > 5242880:
        if on_error:
            on_error('invalid_file')
        raise Exception("File cannot be larger than 50mb")
    return content


def paginate_queryset(query: QuerySet, limit: int = 20, index: int = 1) -> Tuple[Page, Paginator]:
    paginator: Paginator = Paginator(query, limit)
    page: Page = paginator.get_page(index)
    return page, paginator
