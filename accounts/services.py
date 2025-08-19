import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Service xử lý gửi email"""
    
    @staticmethod
    def send_verification_email(user):
        """Gửi email xác thực"""
        try:
            # Tạo token
            token = user.generate_email_verification_token()
            
            # Email context
            context = {
                'user': user,
                'token': token,
                'site_url': settings.SITE_URL,
                'expires_hours': 24
            }
            
            # Render email template
            subject = 'Weather App - Xác thực email của bạn'
            plain_message = f'Mã xác thực của bạn là: {token}\nVui lòng nhập mã này vào ứng dụng để kích hoạt tài khoản.'
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Verification email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            return False