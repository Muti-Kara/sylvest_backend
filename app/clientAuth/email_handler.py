from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from secrets import token_urlsafe

from api.helper import Singleton


class EmailHandler(metaclass=Singleton):
    FROM: str = "sylvestapp@gmail.com"
    EMAIL_URL: str = "http://127.0.0.1:8000/auth/verify-email/"
    
    @staticmethod
    def __generate_token() -> str:
        return token_urlsafe(32)
    
    def send_email(self, *, template_name: str, subject: str, data: dict, to: list[str]) -> None:
        msg_plain: str = render_to_string(f"{template_name}.txt", data)
        msg_html: str = render_to_string(f"{template_name}.html", data)
        
        send_mail(
            subject=subject,
            message=msg_plain,
            html_message=msg_html,
            from_email=self.FROM,
            recipient_list=to
        )
    
    def send_verification_mail(self, user: User) -> str:
        """
        Returns generated token
        """
        token: str = self.__generate_token()
        self.send_email(
            template_name="verification_email",
            subject="Account Verification",
            to=[user.email],
            data={
                'username': user.username,
                'verification_url': f"{self.EMAIL_URL}{token}"
            }
        )
        return token