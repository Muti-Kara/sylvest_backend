from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from subjects.models import Community


class CommunityPagination(PageNumberPagination):
    page_size = 10

    def get_paginated_response(self, data) -> Response:
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'has_next': self.get_next_link() is not None,
            'count': self.page.paginator.count,
            'results': data
        })

    def paginate_queryset(self, queryset, request, view=None) -> list[Community]:
        result: list[Community] = super().paginate_queryset(queryset, request, view)

        return result
