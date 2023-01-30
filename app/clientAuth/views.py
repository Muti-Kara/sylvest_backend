from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.permissions import AllowAny
from dj_rest_auth.app_settings import PasswordResetConfirmSerializer
from dj_rest_auth.views import sensitive_post_parameters_m, PasswordResetView, PasswordResetSerializer
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.forms import PasswordResetForm

from .models import UnapprovedUser


@api_view(('GET',))
@renderer_classes([TemplateHTMLRenderer])
def verify_user(request, user_token):
    try:
        u_user: UnapprovedUser = UnapprovedUser.objects.get(url_token=user_token)
        u_user.verify()
        return Response({'status': "Successfully activated your profile"}, template_name="verify_user.html")
    except ObjectDoesNotExist:
        return Response({'status': "This link has either been used or expired."}, template_name="verify_user.html")


@api_view(['GET'])
def inactive_account(request):
    return Response({
        'status': 'Account is inactive. Verify email.'
    }, template_name="verify_user.html")


class CustomPasswordSerializer(PasswordResetSerializer):
    @property
    def password_reset_form_class(self):
        return PasswordResetForm
    
    def get_email_options(self) -> dict:
        return {
            'html_email_template_name': 'password_reset_email.html'
        }


class CustomPasswordResetView(PasswordResetView):
    serializer_class = CustomPasswordSerializer


class PasswordResetConfirmView(GenericAPIView):
    """
    Password reset e-mail link is confirmed, therefore
    this resets the user's password.

    Accepts the following POST parameters: token, uid,
        new_password1, new_password2
    Returns the success/fail message.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)
    throttle_scope = 'dj_rest_auth'
    renderer_classes = [TemplateHTMLRenderer]

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request: Request, *args, **kwargs):
        return Response(
            {
                'detail': '', 
                'serializer': self.serializer_class,
                'uid': self.kwargs.get("uidb64"),
                'token': self.kwargs.get("token")
            },
            template_name="password_reset.html"
        )

    def post(self, request: Request, *args, **kwargs):
        print(request.data)
        serializer: PasswordResetConfirmSerializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'detail': 'Password could not be changed!',
                    'errors': serializer.error_messages
                },
                template_name="password_reset.html"
            )
        serializer.save()
        return Response(
            {'detail': 'Password has been reset with the new password.'},
            template_name="password_reset.html"
        )