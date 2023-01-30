from rest_framework_simplejwt.views import \
    TokenRefreshView, TokenObtainPairView
from django.urls import path, include

from .views import verify_user, inactive_account, PasswordResetConfirmView, CustomPasswordResetView

urlpatterns = [
    path('', include('dj_rest_auth.urls')),
    path("password-reset/confirm/<uidb64>/<token>/",
         PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/", CustomPasswordResetView.as_view(), name="password-reset"),
    path('register/', include('dj_rest_auth.registration.urls')),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-email/<user_token>/', verify_user, name='verify-email'),
    path('inactive/', inactive_account, name="account_inactive")
]
