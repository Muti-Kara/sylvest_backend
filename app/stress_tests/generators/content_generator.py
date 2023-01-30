from typing import Type

from django.db.models import Model


class ModelGenerator:
    last_id: int
    model: Type[Model]

    def __init__(self, model: Type[Model]) -> None:
        self.model = model
        self.last_id = self.model.objects.all().last().id if self.model.objects.all().exists() else 0

    def generate(self, number: int, **kwargs) -> list['ModelGenerator.model']:
        raise NotImplementedError()
