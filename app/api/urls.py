from django.urls import path, include

from blog.views import *
from chain.views import *
from .views import *
from rest_framework.routers import DefaultRouter
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from blog.views import MasterPostViewSet
from chat.views import *
from subjects.views import *
from recommender.views import update_recommender

router = DefaultRouter()
router.register('communities', CommunityViewSet)
router.register('profiles', ProfileViewSet)
router.register('masterposts', MasterPostViewSet, basename="masterpost")
router.register('events', EventViewSet)
router.register('projects', ProjectViewSet)
router.register('comments', CommentsViewSet)
router.register('users', UserViewSet)
router.register('chainpages', ChainPageViewSet)
router.register('devices', FCMDeviceAuthorizedViewSet)
router.register('formresponses', FormResponseViewSet)
router.register('postimages', PostImageViewSet)
router.register('postvideos', PostVideoViewSet)
router.register('messages', MessageViewSet)
router.register('rooms', RoomViewSet)
router.register('tags', TagViewSet)
router.register('transferrequests', TransferRequestViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('clientAuth.urls')),
    path('device', get_or_register_device),
    path('update_recommender', update_recommender)
]
