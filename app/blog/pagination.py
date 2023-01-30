from typing import Iterable
from datetime import datetime

from django.db.models import QuerySet
from django.contrib.auth.models import User
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from recommender.recommend import Recommender
from blog.models import MasterPost


class MasterPostPagination(PageNumberPagination):
    page_size = 10

    def __init__(self):
        self.post_score: dict | None = None
        self.recommender: Recommender = Recommender()

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

    @staticmethod
    def __recommend_sort(request: Request,
                         posts: QuerySet[MasterPost]) \
            -> QuerySet[MasterPost]:
        recommender = Recommender()
        if not request.user.is_anonymous:
            return recommender.get_recommended_posts(request.user, posts)
        return posts

    @staticmethod
    def __filter_posts(posts: list[MasterPost], request: Request) -> list[MasterPost]:
        user: User = request.user
        print(posts)
        for i in range(len(posts)):
            post: MasterPost = posts[i]
            match post.privacy:
                case MasterPost.Privacy.FOLLOWERS:
                    if user.is_anonymous or not user.profile.is_following(post.author):
                        posts.remove(post)
                        i -= 1
                    continue
                case MasterPost.Privacy.COMMUNITY:
                    if user.is_anonymous or not post.community.is_joined(user):
                        posts.remove(post)
                        i -= 1
                    continue
                case _:
                    continue
        return posts

    def __sort_posts(
            self,
            *,
            sort_type: str = "recommender",
            posts: QuerySet[MasterPost],
            request: Request) -> list[MasterPost]:
        paginated = super().paginate_queryset(posts, request, None)
        match sort_type:
            case "recommender":
                return super().paginate_queryset(
                    self.__recommend_sort(request, posts), request, None)
            case "date":
                return paginated
            case _:
                raise Exception(f"Type not expected: {sort_type}")

    def paginate_queryset(
            self,
            queryset: QuerySet[MasterPost],
            request: Request,
            view=None) -> Iterable[MasterPost]:
        sort_type: str = request.query_params.get("sort", "recommender")
        return self.__filter_posts(posts=self.__sort_posts(
            sort_type=sort_type,
            posts=queryset,
            request=request
        ), request=request)


class CommentPagination(PageNumberPagination):
    page_size = 20

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
