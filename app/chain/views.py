from django.core.files.base import ContentFile
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from django.contrib.auth.models import User

from api.permissions import IsUserOrReadOnly, CanVerify, IsChainVerified
from api.helper import process_base64_image, paginate_queryset
from .level import ChainManager
from .serializers import (
    ChainPageSerializer,
    TransferableUserSerializer,
    TransferRequestSerializer
)
from .pagination import TransferRequestPagination
from .models import ChainPage, TransferRequest


class TransferRequestViewSet(ModelViewSet):
    queryset = TransferRequest.objects.all()
    serializer_class = TransferRequestSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsChainVerified]
    pagination_class = TransferRequestPagination

    chain_manager = ChainManager()

    def list(self, request, *args, **kwargs) -> Response:
        query_set: QuerySet[TransferRequest] = TransferRequest.objects\
            .exclude(verified_by__in=[request.user])
        page_index: int = int(request.query_params.get("page", 1))
        page, paginator = paginate_queryset(
            query_set,
            limit=20,
            index=page_index
        )
        return Response({
            'page_count': paginator.num_pages,
            'count': paginator.count,
            'has_next': page.has_next(),
            'results': TransferRequestSerializer(
                query_set,
                many=True,
                context={'request': request}).data
        })

    @action(detail=True, methods=['PATCH'], permission_classes=[CanVerify])
    def verify_transfer(self, request: Request, pk: int = None) -> Response:
        transfer: TransferRequest = get_object_or_404(TransferRequest, id=pk)
        user: User = request.user
        self.check_object_permissions(request, user)
        transfer.verify(user)
        return Response(
            TransferRequestSerializer(transfer, context={'request': request}).data
        )


class ChainPageViewSet(ModelViewSet):
    queryset = ChainPage.objects.all()
    serializer_class = ChainPageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsUserOrReadOnly]

    chain_manager = ChainManager()
    PAGINATION_LIMIT = 20

    def retrieve(self, request: Request, pk: int = None, *args, **kwargs) -> Response:
        user: User = get_object_or_404(User, id=pk)
        return Response(
            ChainPageSerializer(user.chainpage, context={'request': request}).data
        )

    @action(detail=False, methods=['POST'], permission_classes=[IsChainVerified])
    def stake_levels(self, request: Request) -> Response:
        self.check_permissions(request)
        chain_page: ChainPage = request.user.chainpage
        chain_page.stake_levels()
        return Response({
            'staked_levels': chain_page.staked_level
        }, status=200)

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def transferable_users(self, request: Request) -> Response:
        self.check_permissions(request)
        user: User = request.user
        return Response([
            TransferableUserSerializer(friend.follower).data
            for friend in user.profile.get_followers()
            if friend.follower.chainpage.wallet_address and friend.follower != user
        ])

    @action(detail=True, methods=['POST'], permission_classes=[IsChainVerified])
    def send_token_to_user(self, request: Request, pk: int = None) -> Response:
        user = get_object_or_404(User, id=pk)
        self.check_permissions(request)
        amount: int | None = request.data.get("amount")
        if not amount:
            return Response({'detail': 'bad data'}, status=405)
        if not user.chainpage.is_verified():
            return Response({'detail': 'user is not verified'}, status=405)
        ChainManager().send(
            ChainManager.Functions.SEND_TOKEN,
            request.user.chainpage.wallet_address,
            user.chainpage.wallet_address,
            amount
        )
        return Response({
            'data': self.chain_manager
            .chain_attributes(request.user.chainpage.wallet_address).__dict__()
        })

    @action(detail=False, methods=['POST'], permission_classes=[IsChainVerified])
    def send_token_to_address(self, request: Request) -> Response:
        self.check_permissions(request)
        address: str | None = request.data.get("address")
        amount: int | None = request.data.get("amount")
        if not amount or not address:
            return Response({'detail': 'bad data'}, status=405)
        ChainManager().send(
            ChainManager.Functions.SEND_TOKEN,
            request.user.chainpage.wallet_address,
            address,
            amount
        )
        return Response({
            'data': self.chain_manager
            .chain_attributes(request.user.chainpage.wallet_address).__dict__()
        })

    @action(detail=False, methods=['PATCH'], permission_classes=[IsAuthenticated])
    def verify_account(self, request: Request) -> Response:
        self.check_permissions(request)
        # id_front_image_data: str | None = request.data.get("front")
        # id_back_image_data: str | None = request.data.get("back")
        # if not id_front_image_data or not id_back_image_data:
        #     return Response({'error': 'bad data'}, status=405)
        chain_page: ChainPage = request.user.chainpage
        # front_image: ContentFile = process_base64_image(id_front_image_data)
        # back_image: ContentFile = process_base64_image(id_back_image_data)
        # chain_page.id_front_image = front_image
        # chain_page.id_back_image = back_image
        chain_page.verified_state = ChainPage.VerifiedState.ACCEPTED
        chain_page.save()
        return Response(
            ChainPageSerializer(chain_page, context={'request': request}).data
        )
