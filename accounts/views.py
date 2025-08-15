from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from weather_app.forms import CustomUserCreationForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
import json

# ===== API VIEWS =====

@require_http_methods(['POST'])
@csrf_exempt
def api_register(request):
    """API đăng ký với email verification"""
    try:
        data = request.data
        form = CustomUserCreationForm(data)
        
        if form.is_valid():
            user = form.save(commit=False)
            
            # Kiểm tra email đã tồn tại chưa
            if User.objects.filter(email=user.email).exists():
                return Response({
                    'success': False,
                    'message': 'Email này đã được sử dụng.',
                    'field_errors': {'email': ['Email đã tồn tại']}
                }, status=400)
            
            user.is_active = not settings.REQUIRE_EMAIL_VERIFICATION  # Inactive nếu cần verify
            user.save()
            
            if settings.REQUIRE_EMAIL_VERIFICATION:
                # Gửi email verification
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
                    # Rollback nếu gửi email thất bại
                    user.delete()
                    return Response({
                        'success': False,
                        'message': 'Không thể gửi email xác thực. Vui lòng thử lại sau.'
                    }, status=500)
            else:
                # Không cần verify email
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
                'field_errors': form.errors
            }, status=400)
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Lỗi server'
        }, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
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
@require_http_methods(["POST"])
def api_logout(request):
    """API đăng xuất"""
    try:
        logout(request)
        return JsonResponse({
            'success': True,
            'message': 'Bạn đã đăng xuất thành công'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Lỗi khi đăng xuất'
        }, status=500)

@require_http_methods(["GET"])
def api_check_auth(request):
    """Kiểm tra trạng thái đăng nhập"""
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user_id': request.user.id,
            'username': request.user.username
        })
    else:
        return JsonResponse({
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
        user.verify_email()
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
def resend_verification_email(request):
    """Gửi lại email xác thực"""
    try:
        email = request.data.get('email')
        if not email:
            return Response({
                'success': False,
                'message': 'Vui lòng nhập email'
            }, status=400)
        
        try:
            user = User.objects.get(email=email, email_verified=False)
            
            # Kiểm tra spam (chỉ cho gửi lại sau 5 phút)
            if (user.email_verification_sent_at and 
                timezone.now() < user.email_verification_sent_at + timedelta(minutes=5)):
                return Response({
                    'success': False,
                    'message': 'Vui lòng đợi 5 phút trước khi gửi lại email xác thực'
                }, status=429)
            
            email_sent = EmailService.send_verification_email(user)
            
            if email_sent:
                return Response({
                    'success': True,
                    'message': 'Email xác thực đã được gửi lại. Vui lòng kiểm tra hộp thư.'
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Không thể gửi email. Vui lòng thử lại sau.'
                }, status=500)
                
        except User.DoesNotExist:
            # Không tiết lộ email có tồn tại hay không (security)
            return Response({
                'success': True,
                'message': 'Nếu email này đã đăng ký, bạn sẽ nhận được email xác thực.'
            })
            
    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Lỗi server'
        }, status=500)
