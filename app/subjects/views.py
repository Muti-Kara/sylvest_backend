from django.db.models import QuerySet
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from api.models import Notification
from blog.models import Tag
from chat.models import Room
from chat.serializers import RoomSerializer
from recommender.serializers import RoledUserSerializer
from subjects.pagination import CommunityPagination
from recommender.models import RoledUser, Follow
from api.helper import paginate_queryset
from api.permissions import IsUserOrReadOnly, PublicOrIsInFollowers
from subjects.serializers import (
    UserSerializer,
    ProfileSerializer,
    CommunitySerializer,
    SmallProfileSerializer, SmallCommunitySerializer, NotificationSerializer
)
from subjects.models import Community, Profile
from chat.manager import get_or_create_room


class UserViewSet(ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class ProfileViewSet(ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsUserOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__username', 'title', 'region']

    PAGINATION_LIMIT = 20

    def retrieve(self, request: Request, pk: int = None, *args, **kwargs) -> Response:
        user: User = get_object_or_404(User, id=pk)
        return Response(
            ProfileSerializer(user.profile, context={'request': request}).data
        )

    @action(detail=True, methods=['GET'], permission_classes=[PublicOrIsInFollowers])
    def followers(self, request: Request, pk: int = None) -> Response:
        profile: Profile = get_object_or_404(User, id=pk).profile
        self.check_object_permissions(request, profile)
        page_index: int = int(request.query_params.get("page", 1))
        followers: QuerySet[Follow] = profile.get_followers()
        page, paginator = paginate_queryset(
            followers,
            limit=self.PAGINATION_LIMIT,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': [
                SmallProfileSerializer(follow.follower).data
                for follow in page.object_list
            ]
        })

    @action(detail=True, methods=['GET'], permission_classes=[PublicOrIsInFollowers])
    def following(self, request: Request, pk: int = None) -> Response:
        profile: Profile = get_object_or_404(User, id=pk).profile
        self.check_object_permissions(request, profile)
        page_index: int = int(request.query_params.get("page", 1))
        following: QuerySet[Follow] = profile.get_following()
        page, paginator = paginate_queryset(
            following,
            limit=self.PAGINATION_LIMIT,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': [
                SmallProfileSerializer(follow.followee).data
                for follow in page.object_list
            ]
        })

    @action(detail=True, methods=['GET'], permission_classes=[PublicOrIsInFollowers])
    def communities(self, request: Request, pk: int = None) -> Response:
        profile: Profile = get_object_or_404(User, id=pk).profile
        self.check_object_permissions(request, profile)
        page_index: int = int(request.query_params.get("page", 1))
        query_all: int = int(request.query_params.get("all", 0))
        roles: QuerySet[RoledUser] = profile.get_joined_communities_roles()
        page, paginator = paginate_queryset(
            roles,
            limit=self.PAGINATION_LIMIT,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages if not query_all else 1,
            'count': paginator.count,
            'has_next': page.has_next() if not query_all else False,
            'results': [
                SmallCommunitySerializer(role.community).data
                for role in page.object_list
            ] if not query_all else [
                SmallCommunitySerializer(role.community).data
                for role in roles
            ]
        })

    @action(detail=False, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def edit_interests(self, request: Request) -> Response:
        self.check_permissions(request)
        profile: Profile = request.user.profile
        interests: list[str] | None = request.data.get("interests")
        if not interests:
            return Response(status=405)

        profile_tags: QuerySet[Tag] = profile.interests.all()

        for tag in profile_tags:
            if tag.title not in interests:
                profile.interests.remove(tag)

        for interest in interests:
            if not profile_tags.filter(title=interest).exists():
                tag, created = Tag.objects.get_or_create(title=interest)
                profile.interests.add(tag)

        return Response(ProfileSerializer(profile, context={'request': request}).data)

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def requests(self, request: Request) -> Response:
        self.check_permissions(request)
        user: User = request.user
        requests: list[User] = [
            follow.follower
            for follow in Follow.objects.filter(
                followee=user, 
                follow_status__in=[Follow.Status.REQUEST_SENT,
                                   Follow.Status.REQUEST_SENT_FIRST])
        ]
        return Response(
            SmallProfileSerializer(requests, many=True).data
        )

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def request_count(self, request: Request) -> Response:
        self.check_permissions(request)
        user: User = request.user
        count: int = Follow.objects.filter(
            followee=user, 
            follow_status__in=[Follow.Status.REQUEST_SENT,
                               Follow.Status.REQUEST_SENT_FIRST]).count()
        return Response({
            'count': count
        })

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def recommended_users(self, request: Request) -> Response:
        self.check_permissions(request)
        profile: Profile = request.user.profile
        detailed: int = int(request.query_params.get("detailed", 0))
        page: int = int(request.query_params.get("page", 1))
        recommended: list[User] = profile.friend_recommendation()
        if detailed:
            profiles: list[Profile] = [user.profile for user in recommended if user.is_active]
            return Response(
                ProfileSerializer(
                    profiles,
                    many=True,
                    context={'request': request}
                ).data
            )
        else:
            return Response(
                SmallProfileSerializer(recommended, many=True).data
            )

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def notifications(self, request: Request) -> Response:
        self.check_permissions(request)
        profile: Profile = request.user.profile
        notifications: QuerySet[Notification] = profile.get_notifications()
        page_index: int = int(request.query_params.get("page", 1))
        page, paginator = paginate_queryset(
            notifications,
            limit=50,
            index=page_index
        )
        profile.read_notifications(page.object_list)
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': NotificationSerializer(page.object_list, many=True).data
        })

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def unread_notifications(self, request: Request) -> Response:
        self.check_permissions(request)
        profile: Profile = request.user.profile
        return Response({
            'message': profile.is_message_notifications_unread(),
            'profile': profile.is_profile_notifications_unread()
        })
        
    @action(detail=True, methods=['GET'])
    def link(self, request: Request, pk: int = None) -> Response:
        profile: Profile = get_object_or_404(User, id=pk).profile
        return Response({'link': profile.get_link()})

    @action(detail=True, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def follow(self, request: Request, pk: int = None) -> Response:
        profile: Profile = get_object_or_404(User, id=pk).profile
        self.check_permissions(request)
        profile.follow(request.user)
        return Response({
            'response': ProfileSerializer(profile)
            .follow_status(request.user, profile)
        })

    @action(detail=True, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def follow_request_action(self, request: Request, pk: int = None) -> Response:
        profile: Profile = get_object_or_404(User, id=pk).profile
        self.check_permissions(request)
        follow: Follow = Follow.objects\
            .get(follower=profile.user, followee=request.user)
        accept: bool = request.data.get("action", "ACCEPT_FOLLOW") == "ACCEPT_FOLLOW"
        if accept:
            follow.accept_follow()
        else:
            follow.decline_follow()
        return Response({'data': accept})

    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def chat(self, request: Request, pk: int = None) -> Response:
        profile: Profile = get_object_or_404(User, id=pk).profile
        self.check_permissions(request)
        room: Room = get_or_create_room(request.user, profile.user)
        return Response(
            RoomSerializer(room, context={'request': request}).data
        )


class CommunityViewSet(ModelViewSet):
    queryset = Community.objects.all()
    serializer_class = CommunitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    # TODO: Secure Community with permission classes
    pagination_class = CommunityPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['title']

    PAGINATION_LIMIT = 20

    def perform_create(self, serializer):
        community: Community = serializer.save()
        RoledUser.objects.create(
            user=self.request.user,
            privilege=RoledUser.Roles.admin,
            community=community
        )

    def partial_update(
            self, request: Request, pk: int = None, *args, **kwargs) -> Response:
        user: User = request.user
        community_update_action: str = request.data.get('action')
        community: Community = get_object_or_404(Community, id=pk)
        rolled_user: RoledUser = get_object_or_404(
            RoledUser, user=user, community=community)

        if not community_update_action:
            return Response({
                "error": "bad data"
            }, status=405)
        if rolled_user.can_do(action=community_update_action.split("|")[0]):
            try:
                match community_update_action:
                    case "edit":
                        community.edit(request.data['updated_attributes'])
                    case "roles":
                        community.change_role(
                            request.data["other_user"], request.data["updated_role"])
                    case "users|ban":
                        community.ban_user(request.data["other_user"])
                    case "posts|remove":
                        community.remove_post(request.data['post_id'])
                return Response(
                    CommunitySerializer(
                        community, context={'request': request}).data
                )
            except KeyError as e:
                return Response({
                    "action_performed": True,
                    "error": "bad data",
                    "detail": e
                }, status=405)
        else:
            return Response(
                {"action_performed": False, "error": "unauthorized"}, status=403)

    @action(detail=True, methods=['GET'])
    def members(self, request: Request, pk: int = None) -> Response:
        community: Community = get_object_or_404(Community, id=pk)
        page_index: int = int(request.query_params.get("page", 1))
        query_all: int = int(request.query_params.get("all", 0))
        members: QuerySet[RoledUser] = community.get_members()
        page, paginator = paginate_queryset(
            members,
            limit=self.PAGINATION_LIMIT,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages if not query_all else 1,
            'count': paginator.count,
            'has_next': page.has_next() if not query_all else False,
            'results': [
                RoledUserSerializer(member, context={'request': request}).data
                for member in page.object_list
            ] if not query_all else [
                RoledUserSerializer(member, context={'request': request}).data
                for member in members
            ]
        })
        
    @action(detail=True, methods=['GET'])
    def link(self, request: Request, pk: int = None) -> Response:
        community: Community = get_object_or_404(Community, id=pk)
        return Response({'link': community.get_link()})

    @action(detail=True, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def join(self, request: Request, pk: int = None) -> Response:
        community: Community = get_object_or_404(Community, id=pk)
        self.check_permissions(request)
        return Response({
            'response': community.join(request.user)
        })

    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def chat(self, request: Request, pk: int = None) -> Response:
        community: Community = get_object_or_404(Community, id=pk)
        self.check_permissions(request)
        room: Room = get_object_or_404(Room, community=community)
        return Response(
            RoomSerializer(room, context={'request': request}).data
        )
