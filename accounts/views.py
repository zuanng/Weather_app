from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from accounts.serializers import CustomUserCreationSerializer
from weather_app.models import User
from accounts.services import EmailService
from django.conf import settings
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging
import json

logger = logging.getLogger(__name__)

# ===== API VIEWS =====

@api_view(['POST'])
@csrf_exempt
def api_register(request):
    """API đăng ký với email verification (dùng DRF serializer)"""
    try:
        serializer = CustomUserCreationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = not settings.REQUIRE_EMAIL_VERIFICATION
            user.save(update_fields=['is_active'])

            if settings.REQUIRE_EMAIL_VERIFICATION:
                email_sent = EmailService.send_verification_email(user)
                if email_sent:
                    return Response({
                        'success': True,
                        'message': 'Đăng ký thành công! Vui lòng kiểm tra email để xác thực tài khoản.',
                        'user_id': user.id,
                        'email_verification_required': True,
                        'email': user.email
                    })
                else:
                    user.delete()
                    return Response({
                        'success': False,
                        'message': 'Không thể gửi email xác thực. Vui lòng thử lại sau.'
                    }, status=500)
            else:
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'success': True,
                    'message': 'Đăng ký thành công!',
                    'user_id': user.id,
                    'username': user.username,
                    'token': token.key
                })
        else:
            return Response({
                'success': False,
                'message': 'Có lỗi xảy ra khi đăng ký.',
                'field_errors': serializer.errors
            }, status=400)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Lỗi server'
        }, status=500)
    
@csrf_exempt
@api_view(['POST'])
def api_login(request): 
    """API đăng nhập với kiểm tra email verification"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'success': False,
                'message': 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu'
            }, status=400)
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # Kiểm tra email verification
            if settings.REQUIRE_EMAIL_VERIFICATION and not user.email_verified:
                return Response({
                    'success': False,
                    'message': 'Vui lòng xác thực email trước khi đăng nhập.',
                    'email_verification_required': True,
                    'email': user.email
                }, status=403)
            
            # Kiểm tra account active
            if not user.is_active:
                return Response({
                    'success': False,
                    'message': 'Tài khoản đã bị khóa. Vui lòng liên hệ admin.'
                }, status=403)
            
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'success': True,
                'message': f'Chào mừng {username}!',
                'user_id': user.id,
                'username': user.username,
                'email_verified': user.email_verified,
                'token': token.key
            })
        else:
            return Response({
                'success': False,
                'message': 'Tên đăng nhập hoặc mật khẩu không đúng'
            }, status=401)
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Lỗi server'
        }, status=500)  

@login_required
@csrf_exempt
@api_view(['POST'])
def api_logout(request):
    """API đăng xuất"""
    try:
        logout(request)
        return Response({
            'success': True,
            'message': 'Bạn đã đăng xuất thành công'
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Lỗi khi đăng xuất'
        }, status=500)

@api_view(['GET'])
def api_check_auth(request):
    """Kiểm tra trạng thái đăng nhập"""
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user_id': request.user.id,
            'username': request.user.username
        })
    else:
        return Response({
            'authenticated': False
        })

def verify_email(request, token):
    """Xác thực email qua token"""
    try:
        user = User.objects.get(
            email_verification_token=token,
            email_verified=False
        )
        
        # Kiểm tra token hết hạn
        if user.is_email_verification_expired():
            messages.error(request, 'Link xác thực đã hết hạn. Vui lòng đăng ký lại.')
            return render(request, 'emails/verification_expired.html', {'user': user})
        
        # Xác thực thành công
        user.verify_email(token)
        user.is_active = True  # Kích hoạt tài khoản
        user.save()
        
        # Tạo token cho user
        token_obj, created = Token.objects.get_or_create(user=user)
        
        # Gửi welcome email
        EmailService.send_welcome_email(user)
        
        messages.success(request, f'Tài khoản {user.username} đã được kích hoạt thành công!')
        
        return render(request, 'emails/verification_success.html', {
            'user': user,
            'token': token_obj.key
        })
        
    except User.DoesNotExist:
        messages.error(request, 'Link xác thực không hợp lệ hoặc đã được sử dụng.')
        return render(request, 'emails/verification_failed.html')

@api_view(['POST'])
@csrf_exempt
def api_verify_email(request):
    """API xác thực email qua token"""
    token = request.data.get('token')
    if not token:
        return Response({
            'success': False,
            'message': 'Thiếu token xác thực.'
        }, status=400)

    try:
        user = User.objects.get(
            email_verification_token=token,
            email_verified=False
        )
        if user.is_email_verification_expired():
            return Response({
                'success': False,
                'message': 'Link xác thực đã hết hạn. Vui lòng đăng ký lại.'
            }, status=400)

        user.verify_email(token)
        user.is_active = True
        user.save(update_fields=['email_verified', 'email_verification_token', 'email_verification_sent_at', 'is_active'])

        token_obj, _ = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'message': f'Tài khoản {user.username} đã được kích hoạt thành công!',
            'user_id': user.id,
            'token': token_obj.key
        })
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Link xác thực không hợp lệ hoặc đã được sử dụng.'
        }, status=400)
