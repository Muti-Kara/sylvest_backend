from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from blog.pagination import CommentPagination, MasterPostPagination
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from api.permissions import IsOwnerOrReadOnly
from rest_framework import filters
from rest_framework.exceptions import ValidationError
from django_filters import rest_framework as dj_filters
from django.contrib.auth.models import User
from django.db.models import Q, QuerySet, Model
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import action
from django.core.exceptions import ObjectDoesNotExist

from datetime import datetime

from blog.serializers import (
    MasterPostSerializer,
    CommentSerializer,
    FormResponseSerializer,
    EventPostSerializer,
    PostVideoSerializer,
    PostImageSerializer,
    FundablePostSerializer,
    EventWithLocationSerializer, TagSerializer)
from blog.models import (
    MasterPost,
    Comment,
    FundablePost,
    PostVideo,
    PostImage,
    EventPost,
    FormResponse,
    Tag)
from recommender.models import UserPostRelation, Follow
from subjects.exceptions import InsufficientPrivilege
from subjects.models import Community
from api.helper import paginate_queryset
from subjects.serializers import SmallProfileSerializer


class MasterPostViewSet(viewsets.ModelViewSet):
    model = MasterPost
    queryset = None
    serializer_class = MasterPostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    pagination_class = MasterPostPagination
    filter_backends = [filters.SearchFilter, dj_filters.DjangoFilterBackend]
    filterset_fields = ['post_type', 'author']
    search_fields = ['title', 'region_details__country',
                     'region_details__province']

    def get_queryset(self):
        community_id: str = self.request.query_params.get('community')
        queryset: QuerySet[MasterPost]
        if community_id is None:
            queryset = self.model.objects.all().order_by("-date_posted")
        else:
            community: Community = get_object_or_404(Community, id=int(community_id))
            queryset = community.get_posts(cls=self.model)
        return queryset

    def perform_create(self, serializer):
        try:
            serializer.save(author=self.request.user)
        except InsufficientPrivilege:
            raise ValidationError("User don't have sufficient privilege to take this action.")

    @action(detail=True, methods=['PATCH'], permission_classes=[IsOwnerOrReadOnly])
    def attach_media(self, request: Request, pk: int = None) -> Response:
        post: MasterPost = get_object_or_404(MasterPost, id=pk)
        self.check_object_permissions(request, post)
        data: dict = request.data
        images_data: list[dict] = data.get('images', [])
        videos_data: list[dict] = data.get('videos', [])

        print("images: ", images_data)
        for data in images_data:
            print("data", data)
            try:
                image: PostImage = PostImage.objects.get(id=data['id'])
                post.images.add(image)
            except Exception as e:
                print(f"Error in image: {e}")

        for data in videos_data:
            try:
                video: PostVideo = PostVideo.objects.get(id=data['id'])
                post.videos.add(video)
            except Exception as e:
                print(f"Error in video: {e}")

        post.save()
        return Response(
            MasterPostSerializer(post, context={'request': request}).data
        )

    @action(detail=True, methods=['GET'])
    def likes(self, request: Request, pk: int = None) -> Response:
        post: MasterPost = get_object_or_404(MasterPost, id=pk)
        page_index: int = int(request.query_params.get("page", 1))
        relations: QuerySet[UserPostRelation] = post.get_likes()
        page, paginator = paginate_queryset(
            relations,
            limit=20,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': [
                SmallProfileSerializer(relation.user).data
                for relation in page.object_list
            ]
        })

    @action(detail=True, methods=['PATCH'], permission_classes=[IsOwnerOrReadOnly])
    def add_tags(self, request: Request, pk: int = None) -> Response:
        post: MasterPost = get_object_or_404(MasterPost, id=pk)
        self.check_object_permissions(request, post)
        tag_titles: list[str] | None = request.data.get("tags")
        if not tag_titles:
            return Response(status=405)
        for title in tag_titles:
            tag, created = Tag.objects.get_or_create(title=title)
            tag.posts.add(post)
        return Response(MasterPostSerializer(post, context={'request': request}).data)

    @action(detail=True, methods=['GET'])
    def link(self, request: Request, pk: int = None) -> Response:
        post: MasterPost = get_object_or_404(MasterPost, id=pk)
        return Response({'link': post.get_link()})

    @action(detail=True, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def like(self, request: Request, pk: int = None) -> Response:
        post: MasterPost = get_object_or_404(MasterPost, id=pk)
        self.check_permissions(request)
        return Response({
            'response': post.like(request.user)
        })


class EventViewSet(MasterPostViewSet):
    model = EventPost
    queryset = EventPost.objects.all().order_by('-date_posted')
    serializer_class = EventPostSerializer

    def perform_update(self, serializer):
        instance: EventPost = serializer.save()
        # TODO : send notification to attendies on update

    @action(detail=False, methods=['GET'])
    def with_location(self, request: Request, *args, **kwargs) -> Response:
        events: list[EventPost] = EventPost.objects.all().exclude(
            location__isnull=True).order_by('-date_posted')
        return Response(
            EventWithLocationSerializer(events, many=True, context={'request': request}).data
        )

    @action(detail=True, methods=['GET'])
    def attendees(self, request: Request, pk: int = None) -> Response:
        event: EventPost = get_object_or_404(EventPost, id=pk)
        page_index: int = int(request.query_params.get("page", 1))
        attendees: QuerySet[User] = event.get_attendees()
        page, paginator = paginate_queryset(
            attendees,
            limit=20,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': SmallProfileSerializer(page.object_list, many=True).data

        })

    @action(detail=True, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def attend(self, request: Request, pk: int = None) -> Response:
        post: EventPost = get_object_or_404(EventPost, id=pk)
        self.check_permissions(request)
        attended: bool = post.attend(request.user)
        return Response({
            'attended': attended,
            'data': "Cannot attend to an event which has expired"
        })


class ProjectViewSet(MasterPostViewSet):
    model = FundablePost
    queryset = FundablePost.objects.order_by('-current')
    serializer_class = FundablePostSerializer

    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def fund(self, request: Request, pk: int = None) -> Response:
        self.check_permissions(request)
        user: User = request.user
        amount: int | any = request.data['amount']
        if not request.data['amount']:
            return Response({
                'error': 'Bad Data'
            }, status=405)
        post: FundablePost = get_object_or_404(FundablePost, pk)
        data = post.fund_post(user, int(amount))
        if not data:
            return Response({
                'error': 'transaction could not be made'
            }, status=405)
        return Response({
            'data': data.__dict__()
        })

    @action(detail=True, methods=['POST'], permission_classes=[IsOwnerOrReadOnly])
    def retrieve_token(self, request: Request, pk: int = None) -> Response:
        user: User = request.user
        post: FundablePost = get_object_or_404(FundablePost, id=pk)
        self.check_object_permissions(request, post)
        data = post.retrieve_from_post(user)
        if not data:
            return Response({
                'error': 'transaction could not be made'
            }, status=405)
        return Response({'data': data.__dict__()})

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def retrievable_projects(self, request: Request) -> Response:
        self.check_permissions(request)
        user: User = request.user
        projects = FundablePost.objects.filter(author=user)
        response = FundablePostSerializer(
            instance=projects,
            context={'request': request},
            many=True
        ).data
        return Response(response)

    @action(detail=True, methods=['GET'])
    def contributors(self, request: Request, pk: int = None) -> Response:
        project: FundablePost = get_object_or_404(FundablePost, id=pk)
        page_index: int = int(request.query_params.get("page", 1))
        contributors: QuerySet[User] = project.get_contributors()
        page, paginator = paginate_queryset(
            contributors,
            limit=20,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': SmallProfileSerializer(page.object_list, many=True).data
        })

    @action(detail=True, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def contribute(self, request: Request, pk: int = None) -> Response:
        post: FundablePost = get_object_or_404(FundablePost, id=pk)
        self.check_permissions(request)
        return Response({
            'response': post.contribute(request.user)
        })


class CommentsViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.filter(related_comment__isnull=True).order_by('date_posted')
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, dj_filters.DjangoFilterBackend]
    filterset_fields = ['post']
    pagination_class = CommentPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['GET'])
    def replies(self, request: Request, pk: int = None) -> Response:
        comment: Comment = get_object_or_404(Comment, id=pk)
        replies: QuerySet[Comment] = Comment.objects \
            .filter(related_comment=comment).order_by('date_posted')
        return Response({
            'has_next': False,
            'results': CommentSerializer(replies, many=True, context={'request': request}).data
        })

    @action(detail=True, methods=['GET'])
    def last_reply(self, request: Request, pk: int = None) -> Response:
        comment: Comment = get_object_or_404(Comment, id=pk)
        replies: QuerySet[Comment] = Comment.objects \
            .filter(related_comment=comment).order_by('date_posted').last()
        return Response(CommentSerializer(replies, context={'request': request}).data)

    @action(detail=True, methods=['GET'])
    def likes(self, request: Request, pk: int = None) -> Response:
        comment: Comment = get_object_or_404(Comment, id=pk)
        page_index: int = int(request.query_params.get("page", 1))
        likes: QuerySet[Comment] = comment.get_likes()
        page, paginator = paginate_queryset(
            likes,
            limit=20,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': SmallProfileSerializer(page.object_list, many=True).data
        })

    @action(detail=True, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def like(self, request: Request, pk: int = None) -> Response:
        comment: Comment = get_object_or_404(Comment, id=pk)
        self.check_permissions(request)
        return Response({
            'response': comment.like(request.user)
        })


class FormResponseViewSet(viewsets.ModelViewSet):
    queryset = FormResponse.objects.all().order_by('-date_posted')
    serializer_class = FormResponseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, dj_filters.DjangoFilterBackend]
    filterset_fields = ['post']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostImageViewSet(viewsets.ModelViewSet):
    queryset = PostImage.objects.all()
    serializer_class = PostImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class PostVideoViewSet(viewsets.ModelViewSet):
    queryset = PostVideo.objects.all()
    serializer_class = PostVideoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title']

    def create(self, request: Request, *args, **kwargs) -> Response:
        title: str | None = request.POST.get("title")
        try:
            tag: Tag = self.queryset.get(title=title)
            return Response(self.serializer_class(tag).data)
        except ObjectDoesNotExist:
            return super(TagViewSet, self).create(request, *args, **kwargs)

    @action(detail=True, methods=['GET'])
    def posts(self, request: Request, pk: int = None) -> Response:
        tag: Tag = get_object_or_404(Tag, id=pk)
        posts: QuerySet[MasterPost] = tag.get_posts()
        page_index: int = int(request.query_params.get("page", 1))
        page, paginator = paginate_queryset(
            posts,
            MasterPostPagination.page_size,
            page_index
        )
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': MasterPostSerializer(posts, many=True, context={'request': request}).data
        })

    @action(detail=True, methods=['PATCH'], permission_classes=[IsOwnerOrReadOnly])
    def add_post(self, request: Request, pk: int = None) -> Response:
        tag: Tag = get_object_or_404(Tag, id=pk)
        post_id: int | None = request.data.get("post")
        if post_id is None:
            return Response(status=403)
        post: MasterPost = get_object_or_404(MasterPost, id=post_id)
        self.check_object_permissions(request, post)
        tag.posts.add(post)
        return Response(
            TagSerializer(tag).data
        )

    @action(detail=False, methods=['GET'])
    def recommended(self, request: Request) -> Response:
        tags: QuerySet[Tag] = Tag.objects.exclude(posts=None)[:30]
        return Response(
            TagSerializer(tags, many=True).data
        )
