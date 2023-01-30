from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class TransferRequestPagination(PageNumberPagination):
    page_size = 30

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
