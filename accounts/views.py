from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from weather_app.forms import CustomUserCreationForm
import json

# ===== API VIEWS =====
@csrf_exempt
@require_http_methods(["POST"])
def api_register(request):
    """API đăng ký tài khoản"""
    try:
        data = json.loads(request.body)
        form = CustomUserCreationForm(data)
        
        if form.is_valid():
            user = form.save()
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Đăng ký thành công!',
                'user_id': user.id,
                'username': user.username
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Có lỗi xảy ra khi đăng ký.',
                'errors': form.errors
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dữ liệu JSON không hợp lệ'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Lỗi server'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """API đăng nhập"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse({
                'success': False,
                'message': 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu'
            }, status=400)
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': f'Chào mừng {username}!',
                'user_id': user.id,
                'username': user.username
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Tên đăng nhập hoặc mật khẩu không đúng'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dữ liệu JSON không hợp lệ'
        }, status=400)
    except Exception as e:
        return JsonResponse({
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
