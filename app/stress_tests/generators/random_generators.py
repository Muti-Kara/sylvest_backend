import json
from random import randrange
from typing import Tuple
from requests import get
import os
from abc import ABC

from sylvest_django.settings import BASE_DIR


class RandomGenerator(ABC):
    _items: list[str]

    def __init__(self, file_path: str) -> None:
        self._initialize_generator(file_path)

    def _initialize_generator(self, file_path: str) -> None:
        raise NotImplementedError()

    def get_item(self) -> str:
        return self._items[randrange(0, len(self._items))]


class RandomNameGenerator(RandomGenerator):
    def _initialize_generator(self, file_path: str) -> None:
        with open(file_path, "r") as f:
            self._items = f.readlines()

    def get_item(self) -> str:
        return super().get_item().replace("\n", "").strip()


class RandomFilePicker(RandomGenerator):
    def _initialize_generator(self, file_path: str) -> None:
        self._items = []
        for file in os.listdir(file_path):
            if ".py" in file:
                continue
            self._items.append(f"{file_path}/{file}")

    # def get_item(self) -> str:
    #     return os.path.join(BASE_DIR, "stress_tests", super().get_item())


def random_post_type() -> str:
    return ['PO', 'EV', 'PR'][randrange(0, 3)]


def random_coordinates() -> Tuple[float, float]:
    response = get("https://api.3geonames.org/?randomland=yes").content
    data: dict = json.loads(response)
    return data['geodata']['nearest']['latt'], data['geodata']['nearest']['longt']
